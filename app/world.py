from __future__ import annotations

from typing import Any

from .data import get_stock


def world_scenario(code: str) -> dict[str, Any] | None:
    """Return a self-contained, evidence-first 2D exploration scenario.

    The scenario is intentionally a historical/demo snapshot. The client owns the
    short-lived play session; the server remains the source of the company and
    evidence metadata so a later real-data adapter can replace this fixture.
    """

    stock = get_stock(code)
    if stock is None:
        return None

    if code != "300750":
        return {
            "code": stock.code,
            "name": stock.name,
            "available": False,
            "message": "产业链世界首关目前以宁德时代为演示样本。请从研究台选择宁德时代（300750）进入。",
        }

    return {
        "code": stock.code,
        "name": stock.name,
        "available": True,
        "world_name": "电池环城",
        "subtitle": "宁德时代产业链调查档案",
        "as_of": "演示历史快照 · 非实时数据",
        "notice": "这是研究教育互动，不构成投资建议。所有事实线索均保留来源标签；带“AI 推断”的内容可由玩家一键隐藏。",
        "mission": {
            "id": "lithium-shock",
            "title": "原料风暴：碳酸锂上涨 30% 后，谁先承压？",
            "brief": "沿着上游原料 → 材料 → 电芯 → 下游需求的路径调查，建立一条能被证据支持的影响链。",
            "goal": 4,
            "completion_prompt": "请根据已收集线索，写出一条你认为最合理的传导链。",
        },
        "agents": [
            {
                "id": "archivist",
                "name": "墨",
                "title": "档案官",
                "color": "#81aefc",
                "glyph": "◇",
                "status": "待命",
                "intro": "档案已封存。先看事实，再讲故事。",
            },
            {
                "id": "upstream",
                "name": "岚",
                "title": "上游巡游者",
                "color": "#efbc72",
                "glyph": "⌁",
                "status": "矿区巡查",
                "intro": "原料价格会沿链路走，但不一定原样传到每一站。",
            },
            {
                "id": "downstream",
                "name": "澈",
                "title": "需求观察员",
                "color": "#71d3b7",
                "glyph": "◒",
                "status": "港口待命",
                "intro": "真正决定成本能否传导的，常常是下游需求与议价能力。",
            },
            {
                "id": "risk",
                "name": "赤",
                "title": "风险猎人",
                "color": "#ed8b98",
                "glyph": "✦",
                "status": "等待反驳",
                "intro": "别急着得出结论，我专门负责找你推理链最脆弱的一环。",
            },
        ],
        "nodes": [
            {
                "id": "lithium",
                "label": "盐湖矿区",
                "caption": "上游原料",
                "x": 10,
                "y": 43,
                "color": "#efbc72",
                "agent_id": "upstream",
                "initially_unlocked": True,
                "unlock_after": [],
                "message": "碳酸锂等原材料价格变化，会直接改变电池材料端的成本压力。先记住：价格冲击不等于最终利润冲击，链条还没走完。",
                "clue": {
                    "id": "E-矿-01",
                    "title": "原材料成本线索",
                    "kind": "hard",
                    "source": "演示产业链快照 / 原材料价格字段",
                    "detail": "碳酸锂属于动力电池关键上游材料，价格波动会传导至材料采购成本。",
                },
            },
            {
                "id": "materials",
                "label": "材料工坊",
                "caption": "正极 / 负极 / 电解液",
                "x": 30,
                "y": 24,
                "color": "#d99ad5",
                "agent_id": "upstream",
                "initially_unlocked": False,
                "unlock_after": ["lithium"],
                "message": "材料工坊不是透明管道。库存周期、长协价格和配方差异，都会让同一波原料上涨产生不同的即时影响。",
                "clue": {
                    "id": "E-材-02",
                    "title": "传导存在缓冲层",
                    "kind": "derived",
                    "source": "AI 推断 / 基于库存、长协与材料结构的研究假设",
                    "detail": "原材料价格到电芯成本的传导可能存在滞后，需要查看具体合同与库存数据验证。",
                },
            },
            {
                "id": "battery",
                "label": "电芯城",
                "caption": "宁德时代核心业务",
                "x": 52,
                "y": 47,
                "color": "#81aefc",
                "agent_id": "archivist",
                "initially_unlocked": False,
                "unlock_after": ["materials"],
                "message": f"档案显示：{stock.name}的演示财务快照中，ROE 为 {stock.roe:.1f}%、净利润增速为 {stock.profit_growth:.1f}%。这些指标说明经营结果，不自动解释成本上升由谁承担。",
                "clue": {
                    "id": "E-电-03",
                    "title": "经营结果需要拆因",
                    "kind": "hard",
                    "source": "演示财务快照 / 财务指标字段",
                    "detail": f"ROE {stock.roe:.1f}%，营收增速 {stock.revenue_growth:.1f}%，净利润增速 {stock.profit_growth:.1f}%。",
                },
            },
            {
                "id": "automaker",
                "label": "车企港",
                "caption": "下游客户与竞争",
                "x": 75,
                "y": 29,
                "color": "#71d3b7",
                "agent_id": "downstream",
                "initially_unlocked": False,
                "unlock_after": ["battery"],
                "message": "下游需求强、供给紧时，电池厂更有机会把成本压力转化为价格调整；竞争激烈或终端疲弱时，传导可能被卡在电芯环节。",
                "clue": {
                    "id": "E-车-04",
                    "title": "需求决定议价空间",
                    "kind": "hard",
                    "source": "演示行业需求字段 / 下游关系快照",
                    "detail": "成本是否能够转嫁，需要同时核验客户需求、行业供需与合同定价机制。",
                },
            },
            {
                "id": "storage",
                "label": "储能灯塔",
                "caption": "第二需求出口",
                "x": 87,
                "y": 61,
                "color": "#9aa8ff",
                "agent_id": "downstream",
                "initially_unlocked": False,
                "unlock_after": ["automaker"],
                "message": "储能是另一条需求出口。它不能自动抵消车企需求变化，但能帮助你理解公司并非只依赖一种终端场景。",
                "clue": {
                    "id": "E-储-05",
                    "title": "需求出口多元化",
                    "kind": "derived",
                    "source": "AI 推断 / 基于业务场景的研究假设",
                    "detail": "多元终端需求可能降低单一客户周期的影响，仍需按业务收入与订单数据验证。",
                },
            },
        ],
        "risk_challenge": {
            "title": "风险猎人的反驳",
            "prompt": "你已经走完主链路。现在回答：原材料上涨一定会压缩电池公司的利润吗？",
            "options": [
                {
                    "id": "always",
                    "label": "一定会，成本上涨必然压缩利润。",
                    "response": "过于绝对。你忽略了库存、长协、产品结构与下游议价能力。",
                    "quality": "needs_work",
                },
                {
                    "id": "conditional",
                    "label": "不一定，关键取决于成本传导速度与下游需求强度。",
                    "response": "这条回答保留了条件，并与已收集的成本、材料、电芯和需求线索一致。",
                    "quality": "strong",
                },
                {
                    "id": "none",
                    "label": "不会，公司总能把成本完全转嫁。",
                    "response": "证据不足。市场竞争和需求走弱时，完全转嫁通常难以成立。",
                    "quality": "needs_work",
                },
            ],
        },
        "completion": {
            "title": "你的第一张产业链理解卡",
            "summary": "原材料价格上升会先增加材料端成本压力；能否进一步压缩电池利润，取决于库存与长协缓冲、产品结构，以及下游需求和议价能力。",
            "next_questions": [
                "公司当前原材料库存和长协价格处于什么位置？",
                "下游客户合同中是否存在调价机制？",
                "储能与车企需求的变化能否分散周期风险？",
            ],
        },
    }

