# 行业研究院

多行业行研 agent 集群的容器仓库。共享申万 2021 全市场分类数据源与拉数作业；每个申万一级行业单独估值。

## 当前集群

| 集群 | 路径 | 版本 | v1 覆盖 |
|------|------|------|---------|
| 电子 | `clusters/electronics_research_agent/` | v0.1.0 | 17 只股票（来自 `valuation_inputs`） |

设计见 [DESIGN.md](DESIGN.md)。

## 布局

```text
industry_research_institute/
  industry_data/sw2021/   # 申万 2021 全市场分类基准（31 L1 / 134 L2 / 346 L3 + 成分）
  jobs/                   # 行业 / 财报 / 一致预期拉数作业 → Postgres
  clusters/               # 各一级行业 agent 集群
  .env / .env.example     # Postgres 连接（VR_PG_PASSWORD，gitignore）
```

两层分工：

| 层 | 放什么 | 谁用 |
|----|--------|------|
| 研究院（本目录） | 全市场申万分类树、成分、拉数作业 | 所有行业集群共用 |
| 集群 `clusters/<industry>/` | 该一级的组织编制、playbook、宇宙、本行业估值政策卡 | 只跑本行业研报与估值 |

## 命令

在仓库根目录执行（需 `.env` 中设置 `VR_PG_PASSWORD`）：

```bash
# 拉数作业
python jobs/batch_industry.py            # 申万行业 + 东财板块 → vr_industry_sw / vr_sector_em
python jobs/batch_ths_full_history.py    # 同花顺四表全历史 → vr_ths_main/debt/benefit/cashflow
python jobs/batch_cashflow_only.py       # 仅补现金流量表
python jobs/fetch_consensus.py           # 一致预期双源融合 → vr_consensus_source / vr_consensus_snapshot

# 刷新申万 L3 成分
python industry_data/sw2021/scripts/fetch_l3_members.py
```

电子集群命令见 `clusters/electronics_research_agent/README.md`。

