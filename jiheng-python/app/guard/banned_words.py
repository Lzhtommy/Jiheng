from app.guard.guard_chain import GuardResult

BANNED_WORDS = ["买入", "卖出", "满仓", "空仓", "加杠杆"]


class BannedChecker:
    def check(self, output: dict) -> GuardResult:
        content = str(output.get("content", ""))
        for word in BANNED_WORDS:
            if word in content:
                return GuardResult(passed=False, reason=f"含禁词: {word}")
        return GuardResult(passed=True)
