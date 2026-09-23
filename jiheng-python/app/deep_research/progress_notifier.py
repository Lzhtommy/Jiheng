from app.clients.java_internal import JavaInternalClient


class ProgressNotifier:
    async def notify(self, user_id: str, task_id: str, content: str) -> None:
        await JavaInternalClient().create_notification(
            {
                "user_id": user_id,
                "type": "deep_research_progress",
                "title": "深度研究进度",
                "content": content,
                "task_id": task_id,
            }
        )
