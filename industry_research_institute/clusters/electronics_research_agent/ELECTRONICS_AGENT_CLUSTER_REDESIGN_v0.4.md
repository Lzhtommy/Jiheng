# 电子行业研究集群方案

## 目的

在申万电子（270000）编制与统一估值口径下，自动完成公司到行业的研究，并编译出**可追溯、可对账、可发布的研究报告**。

人只在发布前终审。终审不通过时，系统按裁决最小范围重写，直到通过或本轮停止。

集群交付的是报告，不是会议纪要。报告必须能回答四件事：本轮研究了谁、依据什么口径、结论的证据是什么、哪些地方尚未能下判断。

---

## 1. 产品

一次成功发布包含两层，缺一不可。

**研究状态**：按编制汇总后的结构化底稿，是报告的唯一事实来源。  
**研究报告**：由研究状态编译而成的成稿，是对外与对内的主产物。

同一状态可切出：

- 电子行业总览（本轮宇宙与过滤条件下）
- 某二级 / 三级行业笔记
- 个股一页纸
- 相对上轮增量

写手只编译，不发明状态里没有的股票、数字、口径与判断。核心观点必须带证据；没有证据的句子只能进入「未决」。

两种跑批，同一套契约：

| 模式 | 宇宙 | 用途 |
|------|------|------|
| 巡检 | 默认电子全成分，或按 L2/L3/代码过滤 | 覆盖、口径、异常与空槽 |
| 成稿 | 显式子集（板块、名单或点名代码） | 送审与发布 |

成稿报告的首页必须写明本轮实际宇宙，不得把巡检里的待定段落拼成定论。

---

## 2. 编制与宇宙

### 编制

```text
首席  电子 (270000)
  ├─ 主管 半导体 (270100)
  ├─ 主管 元件 (270200)
  ├─ 主管 光学光电子 (270300)
  ├─ 主管 其他电子Ⅱ (270400)
  ├─ 主管 消费电子 (270500)
  └─ 主管 电子化学品Ⅱ (270600)
```

每个 L2 下按申万树一次建齐全部 L3 研究员岗位。岗位与「本轮有没有票」无关。本轮某 L3 分到 0 只股票，产出合法空笔记（`n_companies=0`），计入编制，不计入已研究覆盖。

### 宇宙

| 名单 | 路径 | 用途 |
|------|------|------|
| 生产宇宙 | `data/sw2021/members_electronics.csv` | 默认跑批 |
| 冒烟夹具 | `data/fixtures/universe_smoke_17.yaml` | CI 与本地冒烟 |

映射规则：

1. 成分表内代码使用表内 L2/L3。
2. 表外且显式传入的代码，按 CLI 策略拒绝或标 `unmapped`。
3. 外部行业字段（如 `class_name`）只作对照备注，申万归属为准。

限流只用运行参数（`--l2` / `--l3` / `--codes` / `--universe`），不改编制。

---

## 3. 角色

角色按判断对象划分。可见面由分派结果决定。

| 角色 | 判断对象 | 系统输入 | 输出 |
|------|----------|----------|------|
| 编排器（代码） | 分派、注卡、装配、闸门、重写路由 | 宇宙、树、政策、库、终审裁决 | 分派结果、Manifest、RewritePlan |
| 研究员 L3 | 本 L3 公司事实、估值情景、相对位置 | 本 L3 股票包、本政策卡、本轮只读输入 | CompanyCard、L3Note |
| 主管 L2 | 下属可比性、口径一致性、本二级位置 | 直属 L3Note、L2 政策、本轮只读输入 | L2Review |
| 首席 L1 | 电子整体、各 L2 相对位置、冲突、优先级 | 各 L2Review、本轮只读输入 | L1Brief |
| 写手 | 把已通过闸门的状态编成报告 | 研究状态、主张-证据表、重写约束 | ResearchReport |
| 终审人 | 本轮成稿能否发布 | 报告、主张-证据表、Manifest | ReviewDecision |

编排器不做行业判断、不改数字、不改政策卡。  
CompanyCard 留在 L3 目录；上交的是 L3Note 中的质控标量与摘要。主管核对数字，读这些字段。

---

## 4. 本轮信息流

```text
只读前提（若本轮提供）
  CycleClock：终端方向、库存、晶圆厂 capex、管制强度、版本与来源
        ↓
分派：U → L3 → 注入政策卡 → 裁剪上下文
        ↓
L3 写卡与 Note，并最多提交 5 条 ChainFact
  （指标、方向或区间、时期、来源字段、置信度）
        ↓
L2 汇总直属 Note + 只读黑板
        ↓
L1 汇总各 L2
        ↓
写手编译报告
        ↓
自动闸门 → 人终审 → 通过发布 / 不通过则按 scope 重写
```

Clock 只读。来源优先级：人预先写入的前提，或上轮已发布报告中冻结的时钟段。L3 须回答相对本钟是顺周期、滞后还是对冲；允许输出 `clock_conflict` 与证据。

ChainFact 供其它 L3 与上级只读，用来做稼动、价格、封装利用率、服务器板占比一类交叉印证。估值表、个股叙事、宇宙外股票不得写入黑板。

向上只传契约字段，不传「我是某研究员」长文。

---

## 5. 工件

| 工件 | 必有内容 |
|------|----------|
| CompanyCard | 代码与名称、申万 L2/L3、对照备注、政策 `spec_id`、主指标、三情景、关键假设、证伪条件、provenance；判断可暂空 |
| L3Note | `n_companies`、政策行、未切片标记、公司摘要（含质控标量）、冲突与异常、时钟应答、ChainFact 列表、主张列表 |
| L2Review | 下属对比结论、政策抽检、本 L2 相对位置、打回/重写记录、主张列表 |
| L1Brief | 各 L2 摘要、跨 L2 冲突点名、关注优先级、本轮宇宙过滤、主张列表 |
| 主张（Claim） | `claim`、`evidence[]`、`assumption[]`、`falsifier[]`、`confidence`、`scope` |
| ResearchReport | `source_run_id`、目录固定成稿、主张-证据表、样本边界 |
| RunManifest | 宇宙来源与规模、过滤、specs 与成分快照、clock 版本、llm、空槽与失败槽、重写史 |
| ReviewDecision | `pass/reject`、`scope`、`reason_codes`、`must_change`、`must_not` |
| RewritePlan | 由裁决生成的最小重写面与硬约束 |

报告固定目录：

1. 本轮结论  
2. 证据  
3. 情景  
4. 冲突与未决  
5. 样本边界（本轮跑了谁）  
6. 附录来源  

`pending` 不得渲染成肯定句。空槽不得写成「已覆盖并认为」。

---

## 6. 估值政策

真源：`data/specs/electronics_specs.yaml`。

- 有 L3 切片用切片；无切片用 L2 默认链，并标 `unsliced=true`。
- 本轮只引用。研究员可附 `policy_change_request`（建议、原因、影响范围）进入待审队列，下一轮在人改 YAML 之后生效。
- 主管抽检主指标是否与卡一致、未切片是否声明。

---

## 7. 运行

```bash
python -m electronics_research_agent run
python -m electronics_research_agent run --l2 270100,270200
python -m electronics_research_agent run --l3 270108
python -m electronics_research_agent run --codes 002371,300054
python -m electronics_research_agent run --universe fixture:smoke_17 --no-db
python -m electronics_research_agent run --mode publish --l2 270100

python -m electronics_research_agent tree
python -m electronics_research_agent map --codes 002371
python -m electronics_research_agent universe
python -m electronics_research_agent universe --fixture smoke_17
```

一次成稿 run：

```text
0. 读树、政策、宇宙、本轮 Clock（若有）
1. 预检：映射、输入 schema、夹具（若启用）
2. U → L3；未映射按策略处理
3. 按 L3 注卡、拉库、裁剪上下文
4. 各 L3 写 Card / Note / Claim / ChainFact（空槽只写空 Note）
5. 各 L2 写 Review
6. L1 写 Brief
7. 写手编译报告
8. 送审闸门
9. 人终审；reject 则按 RewritePlan 回到对应步骤
10. 通过则发布到 runs/{id}/，并计算与上轮数字、归属、主张 diff
```

关 LLM：数字与归属落地，判断与报告中的观点段为 `pending`，结构完整，可巡检。  
开 LLM：按 L3 → L2 → L1 → 写手填判断与成文；汇报顺序不变。

---

## 8. 送审闸门

人看见之前，下列检查全部通过，否则不得送审：

- 每只在宇宙内的股票有且仅有一个 L3
- 政策主链与 YAML 一致；未切片已声明
- 研究员上下文中不含其它 L3 股票列表
- `n_companies=0` 未计入已研究
- 报告中的关键数字 ⊆ 工件数字
- 报告点名的股票 ⊆ 本轮宇宙
- 核心观点每条都有 `evidence`；无证据只进「未决」
- 工件里已记录的口径冲突，报告冲突节非空
- 相对上轮数字已变而对应叙事未变，标 `template_suspect`，不得送审
- Manifest 含宇宙、过滤、specs、成分快照、clock 版本

闸门失败则封闭本轮该出口，能在编译层修复的先重编译，不能的按失败码停在对应槽。

---

## 9. 终审与重写

终审人只输出 `ReviewDecision`，不改 YAML、不改数字、不手改正文。

```text
verdict: pass | reject
scope:   report | l1 | l2:<id> | l3:<id> | blocked
reason_codes: 必填
must_change / must_not: 下一轮硬约束
notes: 可选说明，单独不能触发重写
```

无原因码不得重写。  
`blocked` 表示证据或政策不足，状态冻结，标 `unresolved`。

| 码 | 含义 | 默认重写面 |
|----|------|------------|
| `ungrounded_claim` | 核心观点缺证据 | 写出该主张的那一级 |
| `conflict_omitted` | 已知冲突未进入报告 | 先 `report`，必要时 `l1` |
| `scope_overclaim` | 把子集或空槽写成全行业 | `report` 或 `l1` |
| `template_recycle` | 数字变、叙事未变 | 对应 L3 或 L2 |
| `internal_inconsistency` | 报告与状态矛盾 | `report`（以状态为准） |
| `empty_judgment` | 结构全、判断空 | 对应 L2 或 L3 |
| `wrong_emphasis` | 主次与 L1 优先级不符 | `report` |
| `clock_unanswered` | 有时钟未应答 | 对应 L3 |
| `data_insufficient` | 证据不够成稿 | `blocked` |
| `policy_or_taxonomy` | 口径或归属需改宪法 | `blocked` |

重写取最小面：能只改报告就不改 Brief；能只改一个 L3 就不动其它板块。重写时冻结：申万归属、政策卡、本轮宇宙、库快照、已通过闸门的原始数字。只重写判断、主张-证据与成文，然后向上级联再编译。

预算：

- 人终审每篇最多 2 次
- 同一槽位每轮机器重写最多 2 次
- 编译层每轮最多 2 次（先对账，再考虑下钻状态）

超限或 `blocked`：落盘未通过报告与失败码，停止。  
下一轮同槽可只读挂载已校验的 `must_change`，不能自动写入政策卡。

重写可见面仍受分派约束：L3 只看到本包与本槽约束，写手只看到状态与被拒章节约束。

---

## 10. 目录

```text
electronics_research_agent/
  config/
    settings.yaml          # 可选默认过滤
    db.yaml
    playbooks/             # 通用模板 + L2/L3 名注入；空槽共用 empty_slot.md
  data/
    sw2021/                # 树 + 成分
    specs/                 # 政策卡
    fixtures/              # smoke_17
    clocks/                # 本轮只读时钟（若有）
  src/
    taxonomy / policy / db / orchestrator
    agents / artifacts / report / review
  tests/
  runs/
```

`load_universe()` 默认读成分表；`--universe fixture:…` 读夹具。  
给研究员的上下文对象不含其它 L3 列表。

---

## 11. 测试与指标

| 测试 | 要求 |
|------|------|
| 夹具 smoke_17 | 分派全部正确，政策切片命中，对照备注不覆盖申万 |
| 成分表全量映射 | 一票一 L3，且落在电子树下 |
| 上下文 | 分派 API 不串包 |
| 空槽 | 空 Note 合法，且不计入已研究 |
| 报告对账 | 成稿数字与点名股票不超出状态与宇宙 |
| 终审协议 | 无码不重写；`blocked` 不空转；超限停止 |
| 回归 | 已知夹具反例再次出现即失败 |

| 指标 | 目标 |
|------|------|
| 生产宇宙分派覆盖率 | 有 L3 的股票 100%（未映射走显式策略） |
| 政策命中率 | 100% |
| 空槽假覆盖率 | 0 |
| 送审对账通过率 | 送审稿 100% |
| 核心观点落地率 | 进入「本轮结论」的 claim 100% 有 evidence |
| 夹具反例复发率 | 0 |
| 发布率 | 人终审通过的报告数 / 成稿 run 数（观测，不作唯一 KPI） |

---

## 12. 落地顺序

**P0 底座**  
生产宇宙切换为电子成分；夹具迁出；全树岗位与空槽；关 LLM 跑通 L3→L2→L1 与 Manifest；闸门测试按 §11 先绿。

**P1 主张与报告**  
Claim 契约；L3Note 质控标量齐备；写手编译；数字与股票对账；巡检 / 成稿两种模式。

**P2 终审闭环**  
`ReviewDecision` 与 `RewritePlan`；最小面重写；预算与 `blocked` 路径；发布落盘与上轮 diff。

**P3 成稿质量**  
Clock 作为只读输入接入应答字段；ChainFact 黑板与交叉引用；成稿金标准包（历史已通过报告 + 对应状态）回归「冲突必现、数字变叙事变」。

P0 未绿之前，不开启写手与终审循环。

---

## 13. 验收

下列句子同时为真，方案才算按目的落地：

1. 默认跑批宇宙是电子成分或调用方显式过滤后的子集。  
2. 冒烟 17 票只出现在夹具与测试命令中。  
3. 全树有岗位；无票产出空笔记，且不计入已研究。  
4. 分派决定每级看见的股票与摘要。  ELECTRONICS_AGENT_CLUSTER_REDESIGN_v0.3
5. 估值口径只来自 YAML；变更请求不影响本轮。  
6. 关 LLM 仍能出齐状态与 Manifest。  
7. 开 LLM 的成稿中，核心结论均能指回状态字段或检索来源。  
8. 报告数字与点名股票不超出本轮状态与宇宙。  
9. 人只通过带原因码的裁决触发重写；无码不重写。  
10. 重写按最小 scope 进行；超限或证据不足则停止并留失败码。  
11. 通过终审的报告首页写清本轮研究了谁，冲突与未决不被顺滑叙事抹掉。

---

## 14. 摘要

宪法是申万树与 YAML 政策卡。边界是分派代码。研究是 L3→L2→L1 的状态。报告是状态的编译。质量先靠闸门挡住假口径、假覆盖、无证据的结论，再靠终审人给出可执行否决，由编排器按最小范围重写。

集群的目的是发出去的电子研究报告站得住：覆盖写得清，口径用得对，结论找得到证据，人否决了知道下一稿改哪里。