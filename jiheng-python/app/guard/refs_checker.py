from app.guard.guard_chain import GuardResult


class RefsChecker:
    def check(self, output: dict) -> GuardResult:
        refs = output.get("refs", [])
        if not refs:
            return GuardResult(passed=False, reason="refs 为空")
        return GuardResult(passed=True)
