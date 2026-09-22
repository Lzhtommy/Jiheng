# 静态基准

本目录是 `electronics_research_agent` 的电子子集与估值政策真源。

| 路径 | 内容 |
|------|------|
| `sw2021/l1_electronics.yaml` | 申万一级：电子 `270000` |
| `sw2021/l2_electronics.yaml` | 6 个电子二级（半导体 / 元件 / 光学光电子 / 其他电子Ⅱ / 消费电子 / 电子化学品Ⅱ） |
| `sw2021/l3_electronics.yaml` | 16 个电子三级 |
| `sw2021/name_to_code.yaml` | 电子行业中文名 → 代码 |
| `sw2021/members_electronics.csv` | 电子三级成分股表 |
| `specs/electronics_specs.yaml` | 电子估值政策卡：6 个 L2 spec + 4 个 L3 切片（fabless / foundry / equipment / packaging） |
| `universe/valuation_inputs_v1.yaml` | v1 活跃宇宙：17 只股票冻结名单（含 class_name 与申万归属） |

## 估值政策卡（electronics_specs.yaml）

6 个 L2 默认链：

| L2 | 主链 | 备选 |
|----|------|------|
| 半导体 / 元件 / 消费电子 | PE_TTM → EV_EBITDA → PB | PEG |
| 光学光电子 / 其他电子Ⅱ / 电子化学品Ⅱ | EV_EBITDA → PE_TTM → PB | — |

4 个 L3 切片（仅半导体下属）：

| 切片 | 适用 L3 | 主链 | 禁用 |
|------|---------|------|------|
| fabless | 270104 数字芯片设计 / 270105 模拟芯片设计 | PE_TTM → EV_FCF → PS_TTM | PB、PB_TBV |
| foundry | 270106 集成电路制造 | PB_TBV → EV_EBITDA → EV_FCF | PE_FWD、PEG |
| equipment | 270108 半导体设备 | EV_EBITDA → PB | — |
| packaging | 270107 集成电路封测 | EV_EBITDA → PB | — |

分立器件（270102）、半导体材料（270103）无切片，跟随二级 PE 链并标明「未切片」。