import asyncio

from app.trace.store import TraceStore


def test_trace_store_round_trip(tmp_path):
    store = TraceStore(str(tmp_path))
    trace = {"trace_id": "trace-1", "events": []}
    asyncio.run(store.save(trace))
    assert asyncio.run(store.load("trace-1")) == trace
