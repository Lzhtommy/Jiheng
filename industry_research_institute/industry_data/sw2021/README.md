# 申万行业分类基准（SW2021）

本目录是**行业分类数据与脚本的唯一基准**。各行业集群的估值政策以这里的 registries 为分类真源。

## 目录

```text
industry_data/sw2021/
  source/sw2021_index_classify.md   # 申万 2021 官方分类表原档（含 L1/L2/L3）
  registries/
    l1.yaml                         # 31 个一级
    l2.yaml                         # 134 个二级（含 aliases / spec_id）
    l3.yaml                         # 346 个三级
    name_to_code.yaml               # 中文名 → 官方 code（给同花顺对齐用）
  snapshots/
    sw2021_l3_stock_members.csv     # 三级行业 → 股票代码（精简主表，5205 只股票）
    sw2021_l3_stock_members_enriched.csv   # 富集版（含 L3 元数据）
    l3_members_summary.json         # 最近一次成分拉取摘要（335 个 L3 有成分）
    ths_vr_industry_sw_l1_l2.yaml   # 同花顺落库去重快照
    by_l3/                          # 按三级指数拆分的成分 CSV
  scripts/
    build_registries.py             # 从 source 生成 registries（校验 31/134/346）
    fetch_l3_members.py             # 从申万宏源公开接口刷新 L3 成分股（经 akshare）
    export_ths_snapshot.py          # 从 vr_industry_sw 导出快照并对齐 code
    compare_ths_vs_baseline.py      # THS vs 本基准对账
    fetch_ths_industry_sample.py    # 抽样调用同花顺个股行业接口（调试用）
```

## 数据来源

| 层级 | 基准来源 | 同花顺现状 |
|------|----------|------------|
| L1 / L2 / L3 官方树 | `source/sw2021_index_classify.md`（申万 2021） | — |
| 个股 L1 / L2 | 运行时：`get_10jqka_industry` → `jobs/batch_industry.py` → `vr_industry_sw` | 仅有 L1+L2 中文名，无行业数字码、无 L3 |
| 个股 L3 | `snapshots/sw2021_l3_stock_members*.csv`（申万宏源成分接口） | 同花顺路径无个股 L3 |

L3 成分数据源：`akshare.index_component_sw` → 申万宏源 `swsresearch.com`。按 `registries/l3.yaml` 的指数代码拉取当前成分；官方 346 个三级中部分空壳行业可能无行。

经验证：库内同花顺 L1/L2 中文名与本基准 L2 可 100% 精确对齐（官方多出的空壳 L2 除外）。

## 常用命令

在仓库根目录执行：

```bash
python industry_data/sw2021/scripts/build_registries.py
python industry_data/sw2021/scripts/export_ths_snapshot.py
python industry_data/sw2021/scripts/compare_ths_vs_baseline.py
python industry_data/sw2021/scripts/fetch_ths_industry_sample.py 600519

# 依赖：pip install akshare pandas pyyaml
python industry_data/sw2021/scripts/fetch_l3_members.py
python industry_data/sw2021/scripts/fetch_l3_members.py --write-by-l3
```

## 约定

1. **改分类以本目录为准**：先改 `source/`，再跑 `build_registries.py`。
2. 不要在业务代码里硬编码另一份申万名单。
3. 各行业集群的估值政策在各自 `clusters/*/data/` 内维护；分类真源仍是本目录 `registries/`。
4. `spec_id` 约定：`sw1_<code>` / `sw2_<code>` / `sw3_<code>`。
5. 刷新 L3 成分以 `fetch_l3_members.py` 为准，输出写入 `snapshots/`；CSV 快照应纳入版本库。