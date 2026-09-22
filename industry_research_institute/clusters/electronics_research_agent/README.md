# 电子行研 Agent 集群

申万 2021 **电子（270000）** 一级行业组织成首席 / 主管 / 研究员。不调用估值路由引擎。

本集群位于行业研究院 `industry_research_institute/clusters/`。研究院共享全市场申万数据源与拉数作业，见上两级 [README](../../README.md)。电子内部设计见 [DESIGN.md](DESIGN.md)。

## 组织

1 首席 + 6 主管 + 16 研究员。编制一次建齐，活跃槽位才接票。

| 角色 | 申万层级 | v1 状态 |
|------|----------|---------|
| 首席 | 电子 `270000` | 活跃 |
| 主管 | 半导体 `270100` / 元件 `270200` / 电子化学品Ⅱ `270600` | 活跃 |
| 主管 | 光学光电子 `270300` / 其他电子Ⅱ `270400` / 消费电子 `270500` | stub |
| 研究员 | 7 个三级（设备、分立、封测、材料、PCB、被动元件、电子化学品Ⅲ） | 活跃，对应 17 只股票 |
| 研究员 | 其余 9 个三级 | stub |

## 约定

- 行业树、成分股、估值政策卡在 `data/`
- `src/` 禁止 `import valuation_router`（有 AST 测试守）
- Postgres 密码只来自 `VR_PG_PASSWORD` 或 `.env`

## 命令

在本目录：

```bash
pip install -e .
python -m electronics_research_agent tree                              # 打印组织编制 + 政策
python -m electronics_research_agent universe                          # 列出 v1 宇宙 17 只
python -m electronics_research_agent map --codes 002371,300054         # 股票 → 申万 L1/L2/L3
python -m electronics_research_agent run --no-db                       # 跑批（不连库）
python -m electronics_research_agent run --as-of 2026-09-18            # 跑批（连库富化）
```

未安装时（PowerShell）：

```powershell
$env:PYTHONPATH = "src"
python -m electronics_research_agent map --codes 002371,300054
```

`run` 按 L3 → L2 → L1 写出 `runs/<as-of>/`：

```text
runs/<日期>/
  l3/<l3_code>/note.md | note.json    # 16 个三级笔记
  l2/<l2_code>/review.md | review.json # 6 个二级综述
  l1/brief.md | brief.json             # 一级简报
  manifest.json
```

默认 `llm.enabled=false`：先填结构化数据与草稿综述，叙事栏为「待撰写」。连库前复制 `.env.example` 为 `.env` 填 `VR_PG_PASSWORD`；只读 `valuation_inputs` / `valuation_summary` / `vr_industry_sw` / `vr_finance_snapshot` 四表。

## 测试

```bash
python -m pytest tests
```

覆盖：分派（17 票 / 16 L3 / 6 L2）、政策切片、宇宙映射、禁止路由引擎 import。
