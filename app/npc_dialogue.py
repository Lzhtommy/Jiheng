"""Optional dialogue voice for the procurement journey.

The browser owns the scenario transitions and negotiation record. This module
only phrases an NPC's next line; without a configured model, the authored line
is returned unchanged so the standalone game remains playable.
"""

from __future__ import annotations

import os
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field


SCENE_VOICES = {
    "salt": ("岚", "盐湖矿区现货负责人，直率、会用紧张气氛施压。", "报价牌没有指数和日期；模拟合同样张只写交货日行情。下一站是材料工坊。"),
    "materials": ("岑", "正极材料坊主，擅长讲成本，也在意排产和稳定订单。", "模拟长协写季度调价；库存批次成本未出示。下一站是电芯城。"),
    "cell": ("墨", "电芯商务负责人，克制、重视报价拆分和交期承诺。", "模拟报价只有总价；交付顺序按签约顺序；产线检修为剧情。下一站是车企港。"),
    "port": ("澈", "下游车企采购代表，关心客户的调价节奏和交付风险。", "模拟采购清单按季度调价；替代供应商有一家交期待确认。下一站是储能灯塔。"),
    "storage": ("澈", "储能项目对接人，提醒采购方区分订单、并网和回款。", "模拟台账写储能账期120天、动力业务60天；这些不是企业真实披露。走访结束后回办公室。"),
}
NEXT_PLACES = {
    "salt": "材料工坊",
    "materials": "电芯城",
    "cell": "车企港",
    "port": "储能灯塔",
    "storage": "办公室",
}


class DialogueTurn(BaseModel):
    speaker: Literal["you", "npc"]
    text: str = Field(max_length=550)


class NpcDialogueRequest(BaseModel):
    scene_id: str = Field(max_length=24)
    player_message: str = Field(max_length=240)
    fallback_reply: str = Field(max_length=550)
    history: list[DialogueTurn] = Field(default_factory=list, max_length=8)
    known_scrolls: list[str] = Field(default_factory=list, max_length=20)


def npc_model_enabled() -> bool:
    return all(
        os.getenv(name)
        for name in ("JIHENG_NPC_API_URL", "JIHENG_NPC_API_KEY", "JIHENG_NPC_MODEL")
    )


async def npc_dialogue(request: NpcDialogueRequest) -> dict[str, str]:
    voice = SCENE_VOICES.get(request.scene_id)
    if voice is None:
        return {"reply": request.fallback_reply, "mode": "scripted"}
    if not npc_model_enabled():
        return {"reply": request.fallback_reply, "mode": "scripted"}

    name, personality, facts = voice
    system = (
        f"你在一款产业链走访游戏中扮演{name}。{personality} "
        f"本场景已知事实：{facts} "
        "角色、合同、价格和数字均为虚构情景。"
        "你只负责把给定的剧情回复说得像真人对话，不决定解锁、卷轴、条款或游戏状态。"
        "不得增添事实、金额、比例、交期、承诺、地点或证据，不得把虚构材料说成真实企业披露。"
        "必须保留给定回复中的谈判条件和下一站信息。用第一人称，两到三句，最多180字；只输出角色台词。"
    )
    recent = "\n".join(
        f"{'玩家' if turn.speaker == 'you' else name}：{turn.text}"
        for turn in request.history[-8:]
    )
    user = (
        f"最近对话：\n{recent}\n"
        f"玩家刚说：{request.player_message}\n"
        f"本回合已经确定的剧情回复：{request.fallback_reply}\n"
        "请忠实改写这句剧情回复，保持全部事实和条件。"
    )
    payload = {
        "model": os.environ["JIHENG_NPC_MODEL"],
        "temperature": 0.45,
        "max_tokens": 240,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                os.environ["JIHENG_NPC_API_URL"],
                headers={
                    "Authorization": f"Bearer {os.environ['JIHENG_NPC_API_KEY']}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip() or len(content.strip()) > 450:
            return {"reply": request.fallback_reply, "mode": "scripted"}
        text = content.strip()
        allowed_numbers = set(re.findall(r"\d+(?:\.\d+)?%?", request.fallback_reply))
        produced_numbers = set(re.findall(r"\d+(?:\.\d+)?%?", text))
        next_place = NEXT_PLACES[request.scene_id]
        if not produced_numbers.issubset(allowed_numbers):
            return {"reply": request.fallback_reply, "mode": "scripted"}
        if next_place in request.fallback_reply and next_place not in text:
            return {"reply": request.fallback_reply, "mode": "scripted"}
        return {"reply": text, "mode": "model"}
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return {"reply": request.fallback_reply, "mode": "scripted"}
