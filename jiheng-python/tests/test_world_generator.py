import asyncio
import json

import pytest

from app.agent.world_generator import ScenarioGenerationError, generate_scenario
from app.models.world import GeneratedScenario


def make_scene(prefix: str, claim_scroll_id: str | None = None, cross: dict | None = None) -> dict:
    def topic(topic_id: str, scroll_id: str | None):
        data = {
            "id": topic_id,
            "label": topic_id,
            "prompt": f"关于{topic_id}",
            "keys": ["关键词"],
            "reply": "回应",
            "repeat": "重复回应",
        }
        if scroll_id:
            data["scroll"] = {"id": scroll_id, "title": "单据", "body": "情景模拟，需核对真实来源", "kind": "剧情单据"}
        return data

    return {
        "place": f"{prefix}站点",
        "region": "01 / 上游资源",
        "npc": "岚",
        "role": "负责人",
        "atmosphere": "环境描写",
        "arrival": "抵达旁白",
        "opening": "开场白",
        "generic": "兜底回应",
        "topics": [
            topic("claim", claim_scroll_id),
            topic("proof", None),
            topic("risk", None),
        ],
        "offerPrompt": "提出条件",
        "early": "还太早",
        "offerStrong": "较优条件",
        "offerWeak": "较弱条件",
        "termsStrong": "优条件摘要",
        "termsWeak": "弱条件摘要",
        "risk": "情景模拟，需核对真实来源",
        "lead": "前往下一站",
        "cross": cross or {},
    }


def make_valid_payload() -> dict:
    return {
        "company": {"name": "示例科技", "code": "000001", "tag": "示例 · 中游", "kind": "tech"},
        "scenes": [
            make_scene("一", claim_scroll_id="s1-claim"),
            make_scene("二", cross={"s1-claim": "回应上一站的单据"}),
            make_scene("三"),
            make_scene("四"),
        ],
    }


def test_generated_scenario_rejects_wrong_topic_ids():
    payload = make_valid_payload()
    payload["scenes"][0]["topics"][0]["id"] = "other"
    with pytest.raises(Exception):
        GeneratedScenario.model_validate(payload)


def test_generated_scenario_drops_cross_refs_to_unknown_scrolls():
    payload = make_valid_payload()
    payload["scenes"][1]["cross"]["does-not-exist"] = "幽灵引用"
    scenario = GeneratedScenario.model_validate(payload)
    assert "s1-claim" in scenario.scenes[1].cross
    assert "does-not-exist" not in scenario.scenes[1].cross


def test_generated_scenario_requires_exactly_four_scenes():
    payload = make_valid_payload()
    payload["scenes"] = payload["scenes"][:3]
    with pytest.raises(Exception):
        GeneratedScenario.model_validate(payload)


class FakeChat:
    def __init__(self, replies):
        self.replies = list(replies)

    async def step(self, messages, *, model, tools=None, reasoning=False):
        return {"role": "assistant", "content": self.replies.pop(0)}


def test_generate_scenario_applies_layout_and_ids():
    payload = make_valid_payload()
    chat = FakeChat([json.dumps(payload, ensure_ascii=False)])

    result = asyncio.run(generate_scenario("示例科技", chat=chat))

    assert result["company"]["name"] == "示例科技"
    assert result["company"]["id"].startswith("co-")
    assert len(result["scenes"]) == 4
    assert result["scenes"][0]["id"] == f"{result['company']['id']}-1"
    assert result["scenes"][0]["bg"] == "assets/salt-lake-mine-v1.png"
    assert result["scenes"][2]["bg"] == "assets/battery-cell-hall-v1.png"


def test_generate_scenario_retries_on_invalid_json_then_succeeds():
    payload = make_valid_payload()
    chat = FakeChat(["不是 JSON", json.dumps(payload, ensure_ascii=False)])

    result = asyncio.run(generate_scenario("示例科技", chat=chat))

    assert result["company"]["name"] == "示例科技"


def test_generate_scenario_gives_up_after_retries():
    chat = FakeChat(["不是 JSON", "还是不是 JSON", "仍然不是 JSON"])

    with pytest.raises(ScenarioGenerationError):
        asyncio.run(generate_scenario("示例科技", chat=chat))
