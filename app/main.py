from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data import DEMO_UNIVERSE
from .engine import DATA_NOTICE, diagnosis, debate, screen
from .models import ScreenRequest, ScreenResponse


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="玑衡 AI",
    description="可溯源的 A 股研究辅助工具 MVP",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "demo", "notice": DATA_NOTICE}


@app.get("/api/universe")
def universe() -> dict[str, object]:
    return {
        "data_mode": "demo",
        "notice": DATA_NOTICE,
        "stocks": [{"code": item.code, "name": item.name, "industry": item.industry} for item in DEMO_UNIVERSE],
    }


@app.post("/api/screen", response_model=ScreenResponse)
def screen_stocks(request: ScreenRequest) -> ScreenResponse:
    interpreted, results = screen(request.query)
    return ScreenResponse(query=request.query, interpreted=interpreted, results=results, data_notice=DATA_NOTICE)


@app.get("/api/stocks/{code}/diagnosis")
def stock_diagnosis(code: str) -> dict[str, object]:
    report = diagnosis(code)
    if report is None:
        raise HTTPException(status_code=404, detail="演示股票池中没有这个代码")
    return report


@app.get("/api/stocks/{code}/debate")
def stock_debate(code: str) -> dict[str, object]:
    report = debate(code)
    if report is None:
        raise HTTPException(status_code=404, detail="演示股票池中没有这个代码")
    return report

