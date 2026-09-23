from app.guard.guard_chain import GuardResult

AI_DISCLAIMER = "内容由 AI 生成，请核查重要信息"


class AiDisclaimer:
    def check(self, output: dict) -> GuardResult:
        disclaimer = output.get("ai_disclaimer", "")
        if not disclaimer:
            output["ai_disclaimer"] = AI_DISCLAIMER
        return GuardResult(passed=True)
