import re

from app.guard.guard_chain import GuardResult


class NumericSourceChecker:
    """数值溯源校验"""

    def check(self, output: dict) -> GuardResult:
        content = str(output.get("content", ""))
        if re.search(r"\d+(?:\.\d+)?%", content) and not output.get("refs"):
            return GuardResult(passed=False, reason="数值结论缺少可追溯来源")
        return GuardResult(passed=True)
