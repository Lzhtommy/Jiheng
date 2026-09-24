from app.agent.sources import QUANTIFIED_FACT
from app.guard.guard_chain import GuardResult


class NumericSourceChecker:
    """数值溯源校验"""

    def check(self, output: dict) -> GuardResult:
        content = str(output.get("content", ""))
        if QUANTIFIED_FACT.search(content) and not output.get("refs"):
            return GuardResult(passed=False, reason="数值结论缺少可追溯来源")
        return GuardResult(passed=True)
