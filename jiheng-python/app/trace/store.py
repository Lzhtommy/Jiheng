import json
from pathlib import Path

from app.config import settings


class TraceStore:
    def __init__(self, directory: str | None = None):
        self.directory = Path(directory or settings.trace_store_dir)

    async def save(self, trace: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"{trace['trace_id']}.json").write_text(
            json.dumps(trace, ensure_ascii=False), encoding="utf-8"
        )

    async def load(self, trace_id: str) -> dict | None:
        path = self.directory / f"{trace_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
