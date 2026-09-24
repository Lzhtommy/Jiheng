from app.agent.sources import requires_sources
from app.guard.guard_chain import GuardResult


class RefsChecker:
    def check(self, output: dict) -> GuardResult:
        if requires_sources(str(output.get("question", "")), str(output.get("content", ""))) and not output.get("refs"):
            return GuardResult(passed=False, reason="需要外部事实来源，但 refs 为空")
        return GuardResult(passed=True)
