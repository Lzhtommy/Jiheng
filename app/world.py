from __future__ import annotations

from typing import Any

from .data import get_stock


def world_scenario(code: str) -> dict[str, Any] | None:
    """Return a self-contained, evidence-first 2D exploration scenario.

    The scenario is intentionally a historical/demo snapshot. The client owns the
    short-lived play session; the server remains the source of the company and
    evidence metadata so a later real-data adapter can replace this fixture.

    Each node carries ``x``/``y`` as a percentage position on the single main map,
    laid out around the player standing at the centre. The client renders those
    values directly and must not recompute positions from the chapter grouping.
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
        "chapters": [
            {
                "id": "upstream",
                "number": "01",
                "eyebrow": "上游资源",
                "title": "盐湖矿区",
                "subtitle": "先确认冲击从哪里开始",
                "brief": "原料价格是故事的起点，但起点不等于结论。先把第一条事实证据装进背包。",
                "node_ids": ["lithium"],
                "guide": "我们先不急着判断利润。先确认这次风暴从哪一种原料开始，以及它会先落在哪一层成本上。",
            },
            {
                "id": "materials",
                "number": "02",
                "eyebrow": "中游材料",
                "title": "材料工坊",
                "subtitle": "寻找成本传导的缓冲层",
                "brief": "同一波原料涨价，经过库存、长协和配方之后，可能已经变了形。",
                "node_ids": ["materials"],
                "guide": "这里要特别小心：产业链不是一根透明管道。把‘价格上涨’和‘当期成本上涨’分开看。",
            },
            {
                "id": "battery",
                "number": "03",
                "eyebrow": "核心制造",
                "title": "电芯城",
                "subtitle": "把经营结果拆回原因",
                "brief": "来到公司核心业务，查看经营结果，但不要把一个财务指标直接当成因果解释。",
                "node_ids": ["battery"],
                "guide": "财务指标告诉我们发生了什么，产业链证据才帮助我们追问为什么。现在把两者放在一起。",
            },
            {
                "id": "downstream",
                "number": "04",
                "eyebrow": "下游应用",
                "title": "车企港 · 储能灯塔",
                "subtitle": "判断成本有没有议价出口",
                "brief": "最后看需求和议价能力：车企与储能，是成本压力能否继续传导的两个出口。",
                "node_ids": ["automaker", "storage"],
                "guide": "最后一页要做的是压力测试：需求强不强、客户能不能接受调价，以及公司有没有第二条需求出口。",
            },
        ],
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
                "x": 50,
                "y": 13,
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
                "scene": {
                    "eyebrow": "进入上游资源 / 01",
                    "title": "盐湖矿区",
                    "lesson": {
                        "headline": "盐湖矿区，是电池的原料入口",
                        "plain": "把它想成电池产业链的“菜市场”。这里提供碳酸锂，价格变化会先影响买原料的成本。",
                        "analogy": "像餐厅买菜：菜价上涨，先让进货成本变高，不代表餐厅当天就一定亏钱。",
                        "points": ["它提供电池需要的碳酸锂", "价格变化先进入采购成本", "利润结果还要继续看库存和议价"],
                    },
                    "intro": "矿区的价格看板刚刚跳动。先别急着说谁会亏钱，你要先找出冲击进入产业链的第一站。",
                    "prompt": "碳酸锂上涨 30% 时，第一层影响更可能是什么？",
                    "objects": [
                        {"id": "price_board", "label": "价格看板", "caption": "先确认发生了什么", "detail": "演示快照记录了碳酸锂价格上行。这个事实说明成本环境发生变化，但还没有说明哪家公司最终承担成本。", "kind": "hard"},
                        {"id": "mine_output", "label": "矿区产能", "caption": "看供给是否充足", "detail": "上游供给、产能和库存会影响价格持续多久。价格变化本身，不等同于某一家公司的采购价格当天同步变化。", "kind": "hard"},
                        {"id": "first_link", "label": "第一条传导线", "caption": "把价格连向成本", "detail": "更稳妥的第一步是：原材料价格变化 → 材料采购成本压力。利润影响还需要继续调查。", "kind": "derived"},
                    ],
                    "answers": [
                        {"id": "profit", "label": "电池公司马上亏钱", "feedback": "这是很自然的直觉，但跳得太快了。价格先进入采购成本，中间还隔着库存、合同和议价。", "quality": "needs_work"},
                        {"id": "cost", "label": "先增加材料采购成本压力", "feedback": "很好。你把‘成本冲击的起点’和‘最终利润结果’区分开了。", "quality": "strong"},
                        {"id": "nothing", "label": "和电池产业链无关", "feedback": "不准确。碳酸锂是重要原料，价格变化会进入产业链，只是传导速度和最终承担者还要继续调查。", "quality": "needs_work"},
                    ],
                    "takeaway": "你点亮了第一条因果线：原材料价格变化会先形成材料采购成本压力，还不能直接等同于利润下降。",
                },
            },
            {
                "id": "materials",
                "label": "材料工坊",
                "caption": "正极 / 负极 / 电解液",
                "x": 13,
                "y": 47,
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
                "scene": {
                    "eyebrow": "进入中游材料 / 02",
                    "title": "材料工坊",
                    "lesson": {
                        "headline": "材料工坊，把原料变成电池材料",
                        "plain": "这里不是简单的中转站。正极、负极和电解液会把上游原料加工成电池能用的材料。",
                        "analogy": "像家里的冰箱和长期订货：手里还有存货，今天菜价上涨，也不一定今天就按新价格买。",
                        "points": ["原料要先经过加工", "库存会带来时间缓冲", "长期合同会改变价格传导速度"],
                    },
                    "intro": "你来到材料工坊。这里没有一根透明的成本管道，库存、合同和配方都会改变涨价传导的速度。",
                    "prompt": "为什么原料涨价不会马上变成电芯成本上涨？",
                    "objects": [
                        {"id": "inventory", "label": "库存仓", "caption": "看手里还有多少货", "detail": "如果公司手里还有之前低价买入的库存，短期采购成本可能不会立刻按最新价格跳升。", "kind": "hard"},
                        {"id": "contract", "label": "长协合同", "caption": "看价格怎么约定", "detail": "长期合同可能让价格按照约定节奏调整，原料市场的瞬时波动不一定同步传到本期成本。", "kind": "hard"},
                        {"id": "formula", "label": "材料配方", "caption": "看成本结构是否一样", "detail": "不同产品的材料用量和配方不同。同一个原料价格变化，对不同型号电池的影响也可能不同。", "kind": "derived"},
                    ],
                    "answers": [
                        {"id": "instant", "label": "因为所有成本都会立即同步", "feedback": "这会把产业链想成透明管道，忽略了库存和合同的时间差。", "quality": "needs_work"},
                        {"id": "buffer", "label": "库存、合同和配方会形成缓冲", "feedback": "正确。成本传导不是开关，而是一个有时间差、也有产品差异的过程。", "quality": "strong"},
                        {"id": "unrelated", "label": "因为原料和电池没有关系", "feedback": "不对。它们有关系，只是关系不是即时、单一和完全传递的。", "quality": "needs_work"},
                    ],
                    "takeaway": "你发现了第二条因果线：原料价格到电芯成本之间，存在库存、长协和产品结构形成的缓冲层。",
                },
            },
            {
                "id": "battery",
                "label": "电芯城",
                "caption": "宁德时代核心业务",
                "x": 87,
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
                "scene": {
                    "eyebrow": "进入核心制造 / 03",
                    "title": "电芯城",
                    "lesson": {
                        "headline": "电芯城，是公司把材料做成产品的地方",
                        "plain": "电芯是电池的核心部件。这里的财务数字能告诉你公司表现如何，但数字本身不会自动告诉你原因。",
                        "analogy": "像体检报告：它能告诉你哪项指标变了，但要找出原因，还要结合饮食、运动和病史。",
                        "points": ["材料在这里变成电芯产品", "财务指标描述经营结果", "结果需要和产业链证据一起解释"],
                    },
                    "intro": "你来到公司的核心制造区。这里有一张财务看板，但财务数字只告诉你结果，不会自动告诉你原因。",
                    "prompt": "看到利润变化，能直接说是锂价造成的吗？",
                    "objects": [
                        {"id": "finance_board", "label": "财务看板", "caption": "看经营结果", "detail": f"演示快照中，ROE 为 {stock.roe:.1f}%，营收增速为 {stock.revenue_growth:.1f}%，净利润增速为 {stock.profit_growth:.1f}%。", "kind": "hard"},
                        {"id": "cost_stack", "label": "成本结构", "caption": "把利润拆开看", "detail": "利润变化可能同时受到原料、制造效率、产品结构和售价影响，不能只挑一个最醒目的事件解释全部结果。", "kind": "derived"},
                        {"id": "causal_link", "label": "因果检查台", "caption": "找还缺什么证据", "detail": "要把锂价和利润连起来，还需要验证库存、合同、产品结构和下游调价机制。", "kind": "derived"},
                    ],
                    "answers": [
                        {"id": "direct", "label": "可以，利润变化就是锂价造成的", "feedback": "证据不够。财务结果通常有多个原因，需要继续核验产业链传导。", "quality": "needs_work"},
                        {"id": "split", "label": "不能直接归因，要把结果拆回原因", "feedback": "正确。你已经开始把财务结果和产业链解释分开了。", "quality": "strong"},
                        {"id": "ignore", "label": "财务数据不用看，只看行业故事", "feedback": "也不行。行业故事需要经营数据来约束，否则容易变成没有证据的叙事。", "quality": "needs_work"},
                    ],
                    "takeaway": "你点亮了第三条因果线：财务指标需要和产业链证据放在一起，才能形成可检验的解释。",
                },
            },
            {
                "id": "automaker",
                "label": "车企港",
                "caption": "下游客户与竞争",
                "x": 32,
                "y": 82,
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
                "scene": {
                    "eyebrow": "进入下游应用 / 04A",
                    "title": "车企港",
                    "lesson": {
                        "headline": "车企港，是电池卖给下游客户的地方",
                        "plain": "电池厂做出产品后，要和车企谈订单、价格和交付。下游需求决定它有没有底气谈涨价。",
                        "analogy": "像批发商和大客户谈价：货很抢手时更容易涨价，客户选择很多时就要小心议价能力。",
                        "points": ["车企是重要下游客户", "需求强弱影响谈价能力", "合同条款决定成本能否传导"],
                    },
                    "intro": "车企港的订单正在装船。现在要调查的不是谁更大，而是谁在当前供需关系里拥有更强的议价能力。",
                    "prompt": "电池厂能不能把上涨的成本转嫁给车企？",
                    "objects": [
                        {"id": "order_board", "label": "订单看板", "caption": "看需求强不强", "detail": "如果下游需求强、供给紧，电池厂更有机会和客户讨论价格；需求走弱时，传导会更困难。", "kind": "hard"},
                        {"id": "competition", "label": "竞争航道", "caption": "看客户有没有替代", "detail": "客户选择多、供应商竞争激烈时，单个电池厂的议价能力可能受到限制。", "kind": "hard"},
                        {"id": "pricing_clause", "label": "调价条款", "caption": "看合同能不能传导", "detail": "合同中的调价机制会影响成本变化能否进入销售价格，不能只看市场价格一项。", "kind": "derived"},
                    ],
                    "answers": [
                        {"id": "always", "label": "一定能，客户只能接受", "feedback": "过于绝对。客户需求、竞争和合同共同决定议价空间。", "quality": "needs_work"},
                        {"id": "conditional", "label": "要看需求、竞争和合同机制", "feedback": "正确。成本能否传导，本质上取决于下游的议价条件。", "quality": "strong"},
                        {"id": "never", "label": "一定不能，成本只能自己承担", "feedback": "也过于绝对。供需紧张或合同有调价机制时，部分成本可能传导出去。", "quality": "needs_work"},
                    ],
                    "takeaway": "你点亮了第四条因果线：成本能否转嫁，取决于下游需求、竞争和合同中的议价条件。",
                },
            },
            {
                "id": "storage",
                "label": "储能灯塔",
                "caption": "第二需求出口",
                "x": 68,
                "y": 82,
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
                "scene": {
                    "eyebrow": "进入下游应用 / 04B",
                    "title": "储能灯塔",
                    "lesson": {
                        "headline": "储能灯塔，是电池的另一种需求出口",
                        "plain": "电池不只装在汽车里，也可以用于储能。第二种用途可能帮助公司分散单一客户或单一周期的影响。",
                        "analogy": "像一家餐厅同时服务堂食和外卖：多一种客源有帮助，但要看它的规模和利润贡献。",
                        "points": ["储能是不同于车企的应用场景", "多元需求可能分散单一周期", "有第二条业务不等于风险自动消失"],
                    },
                    "intro": "车企港之外，还有一座储能灯塔。它可能是第二条需求出口，但你需要判断它能否真的分散风险。",
                    "prompt": "有了储能业务，就能自动抵消车企需求下滑吗？",
                    "objects": [
                        {"id": "storage_orders", "label": "储能订单", "caption": "看第二条需求", "detail": "储能可以提供不同于车企的应用场景，但它仍然有自己的客户、价格和周期。", "kind": "hard"},
                        {"id": "mix_board", "label": "业务结构", "caption": "看收入是否足够大", "detail": "业务多元化是否有效，要看不同业务的收入占比、增长和利润贡献，而不是只看有没有这项业务。", "kind": "hard"},
                        {"id": "risk_map", "label": "风险地图", "caption": "看它能否分散周期", "detail": "第二需求出口可能降低单一终端依赖，但不能自动消除原材料、竞争和现金流风险。", "kind": "derived"},
                    ],
                    "answers": [
                        {"id": "offset", "label": "能，第二条业务会完全抵消风险", "feedback": "业务多元化有帮助，但‘完全抵消’需要收入、利润和订单数据支持。", "quality": "needs_work"},
                        {"id": "diversify", "label": "可能分散部分风险，但要看规模和贡献", "feedback": "正确。你没有把‘有第二业务’直接等同于‘风险消失’。", "quality": "strong"},
                        {"id": "irrelevant", "label": "储能和车企无关，不用调查", "feedback": "不对。储能是公司需求结构的一部分，值得作为另一条出口调查。", "quality": "needs_work"},
                    ],
                    "takeaway": "你完成了最后一条调查：多元需求可能分散单一终端风险，但必须继续核验业务规模和利润贡献。",
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
