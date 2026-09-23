import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.event_adapter import as_sse
from app.agent.factory import create_runtime
from app.agent.multi_agent import service as multi_agent
from app.agent.multi_agent.planner import PlanningError
from app.agent.profiles import build_profile
from app.agent.runtime import AgentRunContext
from app.clients.java_internal import JavaInternalClient
from app.config import settings
from app.core.jwt_verify import verify_jwt
from app.core.mode_router import ModeRouter
from app.core.sse_emitter import SseEmitter
from app.models.chat import ChatRequest, MultiAgentRequest, PlanRequest
from app.models.sse_events import (
    DoneEvent,
    ErrorEvent,
    StartEvent,
)
from app.trace.recorder import TraceRecorder

router = APIRouter()
logger = logging.getLogger(__name__)

FlowFactory = Callable[[str], Awaitable[AsyncGenerator[str, None]]]


@router.post("/deep-research", status_code=202)
async def enqueue_deep_research(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    return {"task_id": await _enqueue_deep_research(request, chat_req, payload)}


@router.post("/stream")
async def chat_stream(request: Request, chat_req: ChatRequest, payload: dict = Depends(verify_jwt)):
    if chat_req.mode.value == "deep":
        task_id = await _enqueue_deep_research(request, chat_req, payload)
        return JSONResponse(status_code=202, content={"task_id": task_id})

    async def make_flow(correlation_id: str) -> AsyncGenerator[str, None]:
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
        runtime = create_runtime(settings.chat_runtime)
        return as_sse(runtime.stream(messages, build_profile(routed_mode, expert), context), correlation_id)

    question = next((m.content for m in reversed(chat_req.messages) if m.role == "user"), "")
    return _stream_response(
        chat_req.conversation_id,
        chat_req.mode.value,
        chat_req.expert,
        make_flow,
        user_id=str(payload["sub"]),
        question=question,
    )


@router.post("/multi-agent/plan")
async def multi_agent_plan(plan_req: PlanRequest, payload: dict = Depends(verify_jwt)):
    try:
        plan, tools = await multi_agent.build_plan(plan_req)
    except PlanningError as exc:
        return JSONResponse(status_code=422, content={"message": str(exc)})
    return {"plan": plan.model_dump(), "tools": tools, "max_nodes": settings.multi_agent_max_nodes}


@router.post("/multi-agent/stream")
async def multi_agent_stream(run_req: MultiAgentRequest, payload: dict = Depends(verify_jwt)):
    errors = await multi_agent.plan_errors(run_req.plan)
    if errors:
        return JSONResponse(status_code=422, content={"message": "；".join(errors), "errors": errors})

    async def make_flow(correlation_id: str) -> AsyncGenerator[str, None]:
        executor = await multi_agent.build_executor(run_req)
        return as_sse(executor.stream(), correlation_id)

    question = next((m.content for m in reversed(run_req.messages) if m.role == "user"), "")
    return _stream_response(
        run_req.conversation_id,
        "multi_agent",
        run_req.expert,
        make_flow,
        user_id=str(payload["sub"]),
        question=question,
    )


def _stream_response(
    conversation_id: str,
    mode: str,
    expert: str | None,
    make_flow: FlowFactory,
    *,
    user_id: str | None = None,
    question: str = "",
) -> StreamingResponse:
    correlation_id = str(uuid.uuid4())

    async def event_generator():
        recorder = TraceRecorder(correlation_id, conversation_id, mode)
        completed = True
        answer: list[str] = []
        try:
            yield SseEmitter.start(
                StartEvent(correlation_id=correlation_id, conversation_id=conversation_id, mode=mode, expert=expert)
            )
            flow_iterator = (await make_flow(correlation_id)).__aiter__()
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
                answer.append(_answer_chunk(event))
                yield event

            if completed:
                await _archive_turn(user_id, conversation_id, mode, expert, question, "".join(answer))
                yield SseEmitter.done(DoneEvent(correlation_id=correlation_id))
        except Exception as e:
            logger.warning("对话流异常", exc_info=True)
            message = str(e) or f"服务内部错误（{type(e).__name__}），请稍后重试"
            yield SseEmitter.error(ErrorEvent(correlation_id=correlation_id, code="INTERNAL_ERROR", message=message))
        finally:
            await recorder.save()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _answer_chunk(event: str) -> str:
    """从 message_chunk 事件里取出回答文本，其他事件返回空串。"""
    if not event.startswith("event: message_chunk"):
        return ""
    for line in event.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:]).get("content") or ""
            except json.JSONDecodeError:
                return ""
    return ""


async def _archive_turn(
    user_id: str | None, conversation_id: str, mode: str, expert: str | None, question: str, answer: str
) -> None:
    if not user_id or not question.strip() or not answer.strip():
        return
    try:
        await JavaInternalClient().append_turn(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "question": question,
                "answer": answer,
                "mode": mode,
                "expert": expert,
            }
        )
    except Exception:
        logger.warning("保存对话失败", exc_info=True)


async def _enqueue_deep_research(request: Request, chat_req: ChatRequest, payload: dict) -> str:
    return await request.app.state.task_queue.enqueue(
        {
            "user_id": payload["sub"],
            "conversation_id": chat_req.conversation_id,
            "expert": chat_req.expert,
            "messages": [message.model_dump() for message in chat_req.messages],
        }
    )
