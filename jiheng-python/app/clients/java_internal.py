import httpx

from app.config import settings


class JavaInternalClient:
    """Java 内网接口客户端（携带 Service Token）"""

    def __init__(self):
        self.base_url = settings.java_internal_base_url
        self.headers = {"X-Service-Token": settings.service_token}

    async def get_experts(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
            resp = await client.get(f"{self.base_url}/internal/config/experts", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def get_skill_config(self, skill_id: str) -> dict:
        async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
            resp = await client.get(f"{self.base_url}/internal/config/skills", headers=self.headers)
            resp.raise_for_status()
            skills = resp.json().get("data") or []
            return next((skill for skill in skills if str(skill.get("id")) == str(skill_id)), {})

    async def archive_report(self, report_data: dict) -> dict:
        async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/internal/reports", json=report_data, headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def increment_skill_run(self, skill_id: str):
        async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
            await client.post(f"{self.base_url}/internal/skills/{skill_id}/run", headers=self.headers)

    async def create_notification(self, notification_data: dict):
        async with httpx.AsyncClient(timeout=settings.data_request_timeout_seconds) as client:
            await client.post(f"{self.base_url}/internal/notifications", json=notification_data, headers=self.headers)
