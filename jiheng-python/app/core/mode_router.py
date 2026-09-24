from app.models.chat import ChatMode


class ModeRouter:
    """三模式路由（quick/deep/expert）"""

    @staticmethod
    def route(mode: ChatMode, expert: str | None = None) -> str:
        if mode == ChatMode.EXPERT and not expert:
            return "quick"
        return mode.value
