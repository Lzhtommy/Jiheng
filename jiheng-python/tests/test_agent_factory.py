import asyncio

from app.agent.factory import create_runtime
from app.agent.profiles import build_profile
from app.agent.runtime import AgentEvent, AgentRunContext
from app.config import settings


class BrokenRuntime:
    async def stream(self, messages, profile, context):
        raise RuntimeError("harness unavailable")
        yield


class FakeFallback:
    async def stream(self, messages, profile, context):
        yield AgentEvent("text", {"content": "fallback"})


def test_harness_is_default_runtime():
    assert settings.agent_runtime == "harness-sdk"
    assert create_runtime().__class__.__name__ in {"DeepSeekHarnessRuntime", "FallbackRuntime"}


def test_fallback_requires_explicit_opt_in(monkeypatch):
    from app.agent.factory import FallbackRuntime

    monkeypatch.setattr(settings, "agent_allow_tool_calls_fallback", True)
    runtime = FallbackRuntime(BrokenRuntime(), FakeFallback())
    context = AgentRunContext("user", "conversation")

    async def collect():
        return [event async for event in runtime.stream([], build_profile("quick"), context)]

    events = asyncio.run(collect())
    assert events[0].type == "runtime_fallback"
    assert events[1].data["content"] == "fallback"
