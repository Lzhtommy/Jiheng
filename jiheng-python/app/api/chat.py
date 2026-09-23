import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.event_adapter import as_sse
from app.agent.factory import create_runtime
from app.agent.profiles import build_profile
from app.agent.runtime import AgentRunContext
from app.clients.java_internal import JavaInternalClient
from app.config import settings
from app.core.jwt_verify import verify_jwt
from app.core.mode_router import ModeRouter
from app.core.sse_emitter import SseEmitter
from app.models.chat import ChatRequest
from app.models.sse_events import (
    DoneEvent,
    ErrorEvent,
    StartEvent,
)
from app.trace.recorder import TraceRecorder

router = APIRouter()


@router.post("/deep-research", status_code=202)
async def enqueue_deep_research(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    return {"task_id": await _enqueue_deep_research(request, chat_req, payload)}


@router.post("/stream")
async def chat_stream(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    if chat_req.mode.value == "deep":
        task_id = await _enqueue_deep_research(request, chat_req, payload)
        return JSONResponse(status_code=202, content={"task_id": task_id})

    correlation_id = str(uuid.uuid4())

    async def event_generator():
        recorder = TraceRecorder(correlation_id, chat_req.conversation_id, chat_req.mode.value)
        completed = True
        try:
            yield SseEmitter.start(
                StartEvent(
                    correlation_id=correlation_id,
                    conversation_id=chat_req.conversation_id,
                    mode=chat_req.mode.value,
                    expert=chat_req.expert,
                )
            )

            routed_mode = ModeRouter.route(chat_req.mode, chat_req.expert)
            expert = None
            if routed_mode == "expert":
                experts = await JavaInternalClient().get_experts()
                expert = next(
                    (
                        item
                        for item in experts
                        if item.get("expertId") == chat_req.expert or item.get("expert_id") == chat_req.expert
                    ),
                    None,
                )
            messages = [{"role": m.role, "content": m.content} for m in chat_req.messages]
            context = AgentRunContext(user_id=str(payload["sub"]), conversation_id=chat_req.conversation_id)
            flow = as_sse(
                create_runtime().stream(messages, build_profile(routed_mode, expert), context), correlation_id
            )

            flow_iterator = flow.__aiter__()
            deadline = time.monotonic() + 1800
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    yield SseEmitter.error(
                        ErrorEvent(correlation_id=correlation_id, code="CONNECTION_TIMEOUT", message="对话连接已超时")
                    )
                    completed = False
                    break
                try:
                    event = await asyncio.wait_for(
                        flow_iterator.__anext__(), timeout=min(settings.agent_silent_timeout_seconds, remaining)
                    )
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    yield SseEmitter.error(
                        ErrorEvent(correlation_id=correlation_id, code="MODEL_SILENT_TIMEOUT", message="模型响应超时")
                    )
                    completed = False
                    break
                recorder.record("sse", {"event": event.split("\n", 1)[0]})
                yield event

            if completed:
                yield SseEmitter.done(DoneEvent(correlation_id=correlation_id))
        except Exception as e:
            yield SseEmitter.error(ErrorEvent(correlation_id=correlation_id, code="INTERNAL_ERROR", message=str(e)))
        finally:
            await recorder.save()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _enqueue_deep_research(request: Request, chat_req: ChatRequest, payload: dict) -> str:
    return await request.app.state.task_queue.enqueue(
        {
            "user_id": payload["sub"],
            "conversation_id": chat_req.conversation_id,
            "expert": chat_req.expert,
            "messages": [message.model_dump() for message in chat_req.messages],
        }
    )
