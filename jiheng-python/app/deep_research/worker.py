from app.agent.factory import create_runtime
from app.agent.profiles import build_profile
from app.agent.runtime import AgentRunContext
from app.clients.java_internal import JavaInternalClient
from app.deep_research.progress_notifier import ProgressNotifier


async def deep_research_worker(task: dict) -> None:
    notifier = ProgressNotifier()
    for attempt in range(2):
        try:
            await notifier.notify(task["user_id"], task["task_id"], "已开始研究")
            chunks = []
            context = AgentRunContext(user_id=str(task["user_id"]), conversation_id=task["conversation_id"])
            async for event in create_runtime().stream(task["messages"], build_profile("deep"), context):
                if event.type == "text":
                    chunks.append(event.data["content"])
            await JavaInternalClient().archive_report(
                {
                    "user_id": task["user_id"],
                    "kind": "deep_research",
                    "title": task.get("title", "深度研究报告"),
                    "summary": "深度研究任务已完成",
                    "content": "".join(chunks),
                    "refs": [],
                    "source_conversation_id": task["conversation_id"],
                }
            )
            await notifier.notify(task["user_id"], task["task_id"], "研究完成，报告已归档")
            return
        except Exception:
            if attempt == 1:
                await notifier.notify(task["user_id"], task["task_id"], "研究失败，请稍后重试")
                raise
