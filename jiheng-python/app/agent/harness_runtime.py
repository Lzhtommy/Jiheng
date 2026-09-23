import asyncio
import shutil
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
        if which("dsh") is None:
            raise RuntimeError("Official Harness runtime is installed without the required dsh executable")
        prompt = messages[-1]["content"] if messages else ""
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
                "dsh_home": str(home),
                "cwd": str(workspace),
                "profile": "jiheng",
                "provider": "deepseek-official",
                "model": profile.model,
                "api_key": settings.deepseek_api_key,
                "base_url": settings.deepseek_base_url,
            }
            if profile.reasoning_effort:
                kwargs["reasoning_effort"] = profile.reasoning_effort
            with DeepSeekHarness(
                **kwargs,
            ) as harness:
                return harness.run(prompt, session_id=context.session_key()).final_response

        yield AgentEvent("text", {"content": await asyncio.to_thread(run)})
        yield AgentEvent("refs", {"refs": []})
