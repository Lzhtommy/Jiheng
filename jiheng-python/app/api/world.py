import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.world_generator import ScenarioGenerationError, generate_scenario
from app.clients.java_internal import JavaInternalClient
from app.core.jwt_verify import verify_jwt
from app.core.sse_emitter import SseEmitter
from app.models.sse_events import DoneEvent, ErrorEvent, StageEvent, StartEvent, WorldCompanyEvent
from app.models.world import GenerateCompanyRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-company")
async def generate_company(req: GenerateCompanyRequest, payload: dict = Depends(verify_jwt)):
    correlation_id = str(uuid.uuid4())
    user_id = str(payload["sub"])

    async def event_generator():
        yield SseEmitter.start(
            StartEvent(correlation_id=correlation_id, conversation_id=correlation_id, mode="world")
        )
        yield SseEmitter.stage(
            StageEvent(correlation_id=correlation_id, stage=1, description=f"正在为「{req.company_name}」搭建产业链关卡…")
        )
        try:
            scenario = await generate_scenario(req.company_name)
        except ScenarioGenerationError as exc:
            logger.warning("生成 World 公司关卡失败", exc_info=True)
            yield SseEmitter.error(
                ErrorEvent(correlation_id=correlation_id, code="GENERATION_FAILED", message=str(exc))
            )
            return

        yield SseEmitter.stage(StageEvent(correlation_id=correlation_id, stage=2, description="正在保存关卡…"))
        try:
            saved = await JavaInternalClient().save_world_company(user_id, scenario)
        except Exception:
            logger.warning("保存 World 公司关卡失败", exc_info=True)
            yield SseEmitter.error(
                ErrorEvent(correlation_id=correlation_id, code="PERSIST_FAILED", message="关卡已生成，但保存失败，请重试")
            )
            return

        yield SseEmitter.world_company(WorldCompanyEvent(correlation_id=correlation_id, company=saved or scenario))
        yield SseEmitter.done(DoneEvent(correlation_id=correlation_id))

    return StreamingResponse(event_generator(), media_type="text/event-stream")
