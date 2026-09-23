import time
import uuid

from app.trace.store import TraceStore


class TraceRecorder:
    def __init__(self, correlation_id: str, conversation_id: str, mode: str):
        self.trace = {
            "trace_id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "conversation_id": conversation_id,
            "mode": mode,
            "started_at_ms": int(time.time() * 1000),
            "events": [],
        }

    def record(self, event_type: str, payload: dict) -> None:
        self.trace["events"].append({"type": event_type, "at_ms": int(time.time() * 1000), "payload": payload})

    async def save(self) -> str:
        self.trace["completed_at_ms"] = int(time.time() * 1000)
        await TraceStore().save(self.trace)
        return self.trace["trace_id"]
