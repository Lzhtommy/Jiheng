from typing import Any


class GuardResult:
    def __init__(self, passed: bool, reason: str = "", regenerated: bool = False):
        self.passed = passed
        self.reason = reason
        self.regenerated = regenerated


class GuardChain:
    """后置钩子链"""

    def __init__(self):
        from app.guard.ai_disclaimer import AiDisclaimer
        from app.guard.banned_words import BannedChecker
        from app.guard.numeric_source import NumericSourceChecker
        from app.guard.refs_checker import RefsChecker
        from app.guard.risk_checker import RiskChecker
        from app.guard.source_checker import SourceChecker

        self.checkers = [
            RiskChecker(),
            RefsChecker(),
            BannedChecker(),
            SourceChecker(),
            NumericSourceChecker(),
            AiDisclaimer(),
        ]

    def run(self, output: dict[str, Any]) -> GuardResult:
        for checker in self.checkers:
            result = checker.check(output)
            if not result.passed:
                return result
        return GuardResult(passed=True)
