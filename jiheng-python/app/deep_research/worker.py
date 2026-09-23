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
            refs: list[dict] = []
            context = AgentRunContext(user_id=str(task["user_id"]), conversation_id=task["conversation_id"])
            async for event in create_runtime().stream(task["messages"], build_profile("deep"), context):
                if event.type == "text":
                    chunks.append(event.data["content"])
                elif event.type == "refs":
                    refs = list(event.data.get("refs") or [])
            content = "".join(chunks)
            await JavaInternalClient().archive_report(
                {
                    "user_id": task["user_id"],
                    "kind": "deep_research",
                    "title": task.get("title") or report_title(task["messages"]),
                    "summary": report_summary(content),
                    "content": content,
                    "refs": refs,
                    "source_conversation_id": task["conversation_id"],
                }
            )
            await notifier.notify(task["user_id"], task["task_id"], "研究完成，报告已归档")
            return
        except Exception:
            if attempt == 1:
                await notifier.notify(task["user_id"], task["task_id"], "研究失败，请稍后重试")
                raise


TITLE_PREFIXES = ("深度研究：", "深度研究:", "深度研究", "请帮我", "帮我", "请")


def report_title(messages: list[dict]) -> str:
    question = next((str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"), "")
    title = " ".join(question.split())
    for prefix in TITLE_PREFIXES:
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
            break
    title = title.rstrip("？?。.！!")
    if not title:
        return "深度研究报告"
    return title if len(title) <= 40 else title[:40] + "…"


def report_summary(content: str) -> str:
    for line in content.splitlines():
        text = line.strip().lstrip("#>*-| ").strip()
        if len(text) >= 12:
            return text if len(text) <= 120 else text[:120] + "…"
    return "深度研究已完成，点击查看完整报告。"
