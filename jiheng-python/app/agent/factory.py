from app.agent.harness_runtime import DeepSeekHarnessRuntime
from app.agent.runtime import AgentEvent, AgentRunContext
from app.agent.tool_runtime import DeepSeekToolRuntime
from app.config import settings


class FallbackRuntime:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    async def stream(self, messages: list[dict], profile, context: AgentRunContext):
        emitted = False
        try:
            async for event in self.primary.stream(messages, profile, context):
                emitted = True
                yield event
        except RuntimeError as exc:
            if emitted or not settings.agent_allow_tool_calls_fallback:
                raise
            yield AgentEvent("runtime_fallback", {"reason": str(exc)})
            async for event in self.fallback.stream(messages, profile, context):
                yield event


def create_runtime():
    if settings.agent_runtime == "tool-calls":
        return DeepSeekToolRuntime()
    if settings.agent_runtime != "harness-sdk":
        raise RuntimeError(f"Unsupported agent runtime: {settings.agent_runtime}")
    harness = DeepSeekHarnessRuntime()
    return FallbackRuntime(harness, DeepSeekToolRuntime()) if settings.agent_allow_tool_calls_fallback else harness
