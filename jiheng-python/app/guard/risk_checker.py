from app.guard.guard_chain import GuardResult

RISK_SUFFIX = "以上分析仅供参考，不构成投资建议。"


class RiskChecker:
    def check(self, output: dict) -> GuardResult:
        risk = output.get("risk", "")
        if not risk or not risk.rstrip().endswith(RISK_SUFFIX.rstrip()):
            output["risk"] = (risk + "\n" + RISK_SUFFIX).strip()
        return GuardResult(passed=True)
