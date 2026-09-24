import hashlib
import json
import re

from pydantic import ValidationError

from app.agent.multi_agent.llm import DeepSeekChat
from app.config import settings
from app.models.world import GeneratedScenario

BG_POOL = [
    {"bg": "assets/salt-lake-mine-v1.png", "crop": True},
    {"bg": "assets/materials-workshop-v1.png", "crop": False},
    {"bg": "assets/battery-cell-hall-v1.png", "crop": True},
    {"bg": "assets/downstream-port-v1.png", "crop": True},
]

SYSTEM_PROMPT = """你是「玑衡 World」情景模拟小游戏的关卡编剧。玩家是一名产业研究员，正沿着某家上市公司的产业链，
依次走访「上游」「中游」「下游客户」「第二增长曲线／复盘」四个虚构站点，和每一站的虚构人物对话、听取说法、
索要依据、提出采购或合作条件。你的任务是为用户指定的公司生成这四个站点的剧本内容。

严格只输出一个 JSON 对象，不要输出任何 markdown 代码块标记、注释或多余文字。JSON 结构如下：

{
  "company": {"name": "公司全称", "code": "股票代码，未知留空字符串", "tag": "十字以内的定位标签，例如「动力电池 · 中游」", "kind": "battery|auto|fab|equip|tech 五选一，代表建筑外观风格"},
  "scenes": [
    {
      "place": "站点地名（虚构或半虚构，贴合该环节，如“XX原料基地”）",
      "region": "两位数编号 / 环节名，如 01 / 上游资源",
      "npc": "人物姓氏或称呼（1-2字，如“岚”）",
      "role": "人物身份，如“现货负责人”",
      "atmosphere": "一句环境描写",
      "arrival": "玩家抵达时的旁白，1-2句",
      "opening": "NPC 的开场白，站在自己立场上，带一点防御性或试探",
      "generic": "当玩家闲聊或说得含糊时 NPC 的兜底回应",
      "topics": [
        {"id": "claim", "label": "四字以内按钮标签", "prompt": "玩家发起提问的原话", "keys": ["3-6个中文关键词，用于匹配玩家输入"], "reply": "NPC 第一次回答，避免正面承认所有说法，留有余地", "repeat": "玩家重复问同一话题时的简短重复回应", "scroll": {"id": "全局唯一的英文短id，如 xxx-claim", "title": "单据标题", "body": "1-2句单据内容，强调是情景模拟、需核对真实来源", "kind": "剧情单据"}},
        {"id": "proof", "同上结构，聚焦“依据/合同/条款”类追问"},
        {"id": "risk", "同上结构，聚焦“交付/断供/产能”类追问"}
      ],
      "offerPrompt": "玩家主动提出条件时的引导句",
      "early": "对话深度不足时拒绝谈条件的回应",
      "offerStrong": "玩家已掌握依据（proof）时达成的较优条件说法",
      "offerWeak": "玩家依据不足时达成的较弱条件说法",
      "termsStrong": "较优条件的简短书面总结（十几字）",
      "termsWeak": "较弱条件的简短书面总结",
      "risk": "本站风险提示，必须包含“情景模拟”或“虚构”等字样，提醒需核对真实来源",
      "lead": "NPC 引导玩家前往下一站的一句话，可提及下一站地点或人物",
      "cross": {}
    }
  ]
}

硬性规则：
1. scenes 数组必须恰好 4 个元素，按上游→中游→下游客户→第二增长曲线/复盘 的顺序。
2. 每个 scene 的 topics 数组必须恰好 3 个元素，id 分别是 "claim"、"proof"、"risk"（顺序不限，id 不能改写成别的词）。
3. 每个 topic.scroll.id 必须是仅含小写字母、数字、短横线的全局唯一字符串。
4. cross 字段一律输出 {}（留空，由程序后续处理），不要自己编造键值。
5. 所有人物、合同条款、数字、单据均为虚构教学场景，risk 与 scroll.body 中必须明确提示这一点。
6. 内容使用简体中文，语气克制、专业，避免虚假承诺或投资建议，不出现“买入/卖出/满仓”等措辞。
"""


class ScenarioGenerationError(Exception):
    pass


def _slug(company_name: str) -> str:
    digest = hashlib.sha1(company_name.encode("utf-8")).hexdigest()[:10]
    return f"co-{digest}"


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("模型未返回可解析的 JSON")
    return json.loads(cleaned[start : end + 1])


def _apply_layout(company_id: str, scenario: GeneratedScenario) -> dict:
    scenes = []
    for index, scene in enumerate(scenario.scenes):
        layout = BG_POOL[index % len(BG_POOL)]
        payload = scene.model_dump()
        payload["id"] = f"{company_id}-{index + 1}"
        payload["bg"] = layout["bg"]
        payload["crop"] = layout["crop"]
        scenes.append(payload)
    return {
        "company": {"id": company_id, **scenario.company.model_dump()},
        "scenes": scenes,
    }


async def generate_scenario(company_name: str, chat=None) -> dict:
    company_name = company_name.strip()
    if not company_name:
        raise ScenarioGenerationError("公司名称不能为空")

    chat = chat or DeepSeekChat()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"公司名称：{company_name}"},
    ]
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            message = await chat.step(messages, model=settings.deepseek_model_deep, reasoning=False)
            content = message.get("content") or ""
            raw = _extract_json(content)
            scenario = GeneratedScenario.model_validate(raw)
            return _apply_layout(_slug(company_name), scenario)
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            messages.append(
                {
                    "role": "user",
                    "content": f"上一次输出解析或校验失败：{exc}。请严格只输出符合要求的 JSON，不要包含其他文字。",
                }
            )
    raise ScenarioGenerationError(f"生成「{company_name}」的关卡失败：{last_error}")
