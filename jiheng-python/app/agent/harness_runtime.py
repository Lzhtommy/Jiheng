import asyncio
import json
import os
import shutil
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from shutil import which

from app.agent.profiles import AgentProfile
from app.agent.runtime import AgentEvent, AgentRunContext
from app.agent.sources import add_sources, requires_sources
from app.config import settings


class DeepSeekHarnessRuntime:
    """Official SDK adapter using a per-user, per-conversation restricted profile."""

    async def stream(
        self, messages: list[dict], profile: AgentProfile, context: AgentRunContext
    ) -> AsyncGenerator[AgentEvent, None]:
        try:
            from deepseek_harness import DeepSeekHarness
        except ImportError as exc:
            raise RuntimeError("Install the harness extra from DeepSeek's official distribution first") from exc
        interpreter_dir = os.path.dirname(sys.executable)
        dsh_bin = which("dsh") or which("dsh", path=interpreter_dir)
        if dsh_bin is None:
            raise RuntimeError("Official Harness runtime is installed without the required dsh executable")
        prompt = _build_prompt(messages)
        workspace = context.root(settings.dsh_workspace)
        home = context.root(settings.dsh_home)
        workspace.mkdir(parents=True, exist_ok=True)
        if not home.exists():
            template = Path(settings.dsh_template_home).resolve()
            if not template.is_dir():
                raise RuntimeError(f"Harness template home is missing: {template}")
            shutil.copytree(template, home)
        patch = Path(settings.harness_profile_patch).resolve()
        if not patch.is_file():
            raise RuntimeError(f"Harness profile patch is missing: {patch}")
        profile_dir = home / "profiles" / "jiheng"
        profile_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(patch, profile_dir / "cordis.patch.yml")

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_notification(notification) -> None:
            if notification.method == "session.event":
                event = notification.payload.get("event")
                if isinstance(event, dict):
                    loop.call_soon_threadsafe(queue.put_nowait, event)

        def run() -> str:
            kwargs = {
                "dsh_bin": dsh_bin,
                "dsh_home": str(home),
                "cwd": str(workspace),
                "profile": "jiheng",
                "provider": "deepseek-official",
                "model": profile.model,
                "api_key": settings.deepseek_api_key,
                "base_url": settings.deepseek_base_url,
                # MCP 数据服务以 `python -m app.mcp.server` 启动，需要项目根目录和装好依赖的解释器
                "env": {
                    "DSH_SYSTEM_PROMPT": profile.system_prompt,
                    "JIHENG_APP_ROOT": settings.app_root,
                    "PATH": interpreter_dir + os.pathsep + os.environ.get("PATH", ""),
                },
            }
            if profile.reasoning_effort:
                kwargs["reasoning_effort"] = profile.reasoning_effort
            with DeepSeekHarness(
                **kwargs,
            ) as harness:
                # 每次请求都会新起 dsh 进程，而 SDK 无法续接已落盘的会话，复用 id 会报 already exists
                session_id = f"{context.session_key()}-{uuid.uuid4().hex[:8]}"
                return harness.run(prompt, session_id=session_id, on_notification=on_notification).final_response

        task = asyncio.create_task(asyncio.to_thread(run))
        task.add_done_callback(lambda _: loop.call_soon_threadsafe(queue.put_nowait, None))
        tool_names: dict[str, str] = {}
        refs: dict[str, dict] = {}
        try:
            while (event := await queue.get()) is not None:
                for agent_event in _translate(event, tool_names, refs):
                    yield agent_event
            final = await task
        finally:
            if not task.done():
                task.cancel()
        if profile.mode == "expert" and not refs and requires_sources(str(messages[-1].get("content", "")), final):
            final = "暂未取得可核验的数据来源，因此无法给出可靠的事实性分析。请稍后重试或缩小查询范围。"
        yield AgentEvent("text", {"content": final})
        yield AgentEvent("refs", {"refs": list(refs.values())})


TOOL_PREFIX = "mcp__jiheng_data__"
MAX_TOOL_RESULT_CHARS = 4000


def _translate(event: dict, tool_names: dict[str, str], refs: dict[str, dict]) -> list[AgentEvent]:
    data = event.get("data") or {}
    if event.get("type") == "tool/call":
        call_id = str(data.get("callId", ""))
        name = str(data.get("name", "")).removeprefix(TOOL_PREFIX)
        tool_names[call_id] = name
        return [AgentEvent("tool_call", {"id": call_id, "name": name, "arguments": _parse_json(data.get("arguments"))})]
    if event.get("type") == "tool/result":
        events = []
        for block in (data.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool-result":
                continue
            call_id = str(block.get("toolCallId", ""))
            text = "".join(str(part.get("text", "")) for part in block.get("content") or [] if isinstance(part, dict))
            _collect_refs(text, refs)
            success = not block.get("isError")
            payload = text if len(text) <= MAX_TOOL_RESULT_CHARS else text[:MAX_TOOL_RESULT_CHARS] + "\n…（已截断）"
            events.append(
                AgentEvent(
                    "tool_result",
                    {
                        "id": call_id,
                        "name": tool_names.get(call_id, ""),
                        "success": success,
                        "result": payload,
                        "error": payload,
                    },
                )
            )
        return events
    return []


def _parse_json(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _collect_refs(text: str, refs: dict[str, dict]) -> None:
    result = _parse_json(text)
    if not isinstance(result, dict):
        return
    add_sources(refs, result.get("sources") or [])


MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS = 2000


def _build_prompt(messages: list[dict]) -> str:
    if not messages:
        return ""
    current = messages[-1]["content"]
    history = messages[:-1][-MAX_HISTORY_MESSAGES:]
    if not history:
        return current
    lines = [
        f"{'用户' if m.get('role') == 'user' else '助手'}：{str(m.get('content', ''))[:MAX_HISTORY_CHARS]}"
        for m in history
    ]
    return "以下是本次对话之前的内容，供理解上下文：\n" + "\n".join(lines) + f"\n\n当前问题：{current}"
