from app.guard.guard_chain import GuardResult


class SourceChecker:
    """机构观点来源标注校验"""

    def check(self, output: dict) -> GuardResult:
        content = str(output.get("content", ""))
        if "机构" in content and "来源" not in content:
            return GuardResult(passed=False, reason="机构观点缺少来源标注")
        return GuardResult(passed=True)
