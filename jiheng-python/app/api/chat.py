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
from app.core.abort_manager import AbortManager
from app.core.conversation_guard import ConversationGuard
from app.core.jwt_verify import verify_jwt
from app.core.mode_router import ModeRouter
from app.core.sse_emitter import SseEmitter
from app.deep_research.task_queue import TaskQueue
from app.models.chat import AbortRequest, ChatRequest
from app.models.sse_events import (
    AbortedEvent,
    DoneEvent,
    ErrorEvent,
    StartEvent,
)
from app.trace.recorder import TraceRecorder

router = APIRouter()


@router.post("/deep-research", status_code=202)
async def enqueue_deep_research(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    task_id = await TaskQueue(request.app.state.redis).enqueue(
        {
            "user_id": payload["sub"],
            "conversation_id": chat_req.conversation_id,
            "expert": chat_req.expert,
            "messages": [message.model_dump() for message in chat_req.messages],
        }
    )
    return {"task_id": task_id}


@router.post("/stream")
async def chat_stream(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    if chat_req.mode.value == "deep":
        task_id = await TaskQueue(request.app.state.redis).enqueue(
            {
                "user_id": payload["sub"],
                "conversation_id": chat_req.conversation_id,
                "expert": chat_req.expert,
                "messages": [message.model_dump() for message in chat_req.messages],
            }
        )
        return JSONResponse(status_code=202, content={"task_id": task_id})

    correlation_id = str(uuid.uuid4())
    redis = request.app.state.redis

    guard = ConversationGuard(redis)
    abort_mgr = AbortManager(redis)

    if not await guard.acquire(chat_req.conversation_id):
        return StreamingResponse(
            _error_stream(correlation_id, "CONVERSATION_BUSY", "同一会话已有进行中对话"),
            media_type="text/event-stream",
        )

    await abort_mgr.register(chat_req.conversation_id)

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
                    event = await asyncio.wait_for(flow_iterator.__anext__(), timeout=min(60, remaining))
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    yield SseEmitter.error(
                        ErrorEvent(correlation_id=correlation_id, code="MODEL_SILENT_TIMEOUT", message="模型响应超时")
                    )
                    completed = False
                    break
                if await abort_mgr.is_aborted(chat_req.conversation_id):
                    yield SseEmitter.aborted(AbortedEvent(correlation_id=correlation_id, reason="user_abort"))
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
            await guard.release(chat_req.conversation_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/abort")
async def abort_chat(request: Request, abort_req: AbortRequest, payload: dict = Depends(verify_jwt)):
    redis = request.app.state.redis
    guard = ConversationGuard(redis)
    if not await redis.exists(guard.KEY_PREFIX + abort_req.conversation_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="CONVERSATION_NOT_FOUND")
    abort_mgr = AbortManager(redis)
    await abort_mgr.abort(abort_req.conversation_id)
    return {"success": True}


async def _error_stream(correlation_id: str, code: str, message: str):
    yield SseEmitter.error(ErrorEvent(correlation_id=correlation_id, code=code, message=message))
