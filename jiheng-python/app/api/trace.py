from fastapi import APIRouter, HTTPException

from app.trace.store import TraceStore

router = APIRouter()


@router.get("/{trace_id}/replay")
async def replay_trace(trace_id: str):
    trace = await TraceStore().load(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="TRACE_NOT_FOUND")
    return trace
