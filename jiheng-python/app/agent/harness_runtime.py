import asyncio
import os
import shutil
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from shutil import which

from app.agent.profiles import AgentProfile
from app.agent.runtime import AgentEvent, AgentRunContext
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
                return harness.run(prompt, session_id=session_id).final_response

        yield AgentEvent("text", {"content": await asyncio.to_thread(run)})
        yield AgentEvent("refs", {"refs": []})


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
