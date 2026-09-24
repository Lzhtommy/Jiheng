# 数据作业

**拉数作业**。行业研究院按一级行业单独估值。

## 脚本

| 脚本 | 作用 | 写入表 |
|------|------|--------|
| `batch_industry.py` | 并发抓取申万行业（同花顺）+ 东财板块，过滤北交所，每 100 只入库一次 | `vr_industry_sw`、`vr_sector_em` |
| `batch_ths_full_history.py` | 同花顺全历史财务报表（main / debt / benefit / cash 四表），处理「亿/万/%」单位转换 | `vr_ths_main`、`vr_ths_debt`、`vr_ths_benefit`、`vr_ths_cashflow` |
| `batch_cashflow_only.py` | 仅补现金流量表，查已有股票只拉缺失的 | `vr_ths_cashflow` |
| `fetch_consensus.py` | 一致预期双源融合：同花顺 F10（EPS/净利）+ 东财 RPT_WEB_RESPREDICT（评级/目标价），双源 EPS 差异超 10% 设 conflict_flag | `vr_consensus_source`、`vr_consensus_snapshot` |
| `fetchers/api_fetchers.py` | 第三方 API 封装：`get_eastmoney_industry`、`get_eastmoney_sectors`、`get_10jqka_industry` | — |
| `db_config.py` | Postgres 连接配置；密码只从 `VR_PG_PASSWORD` 读取，缺失抛 `RuntimeError` | — |

## 命令

在 `industry_research_institute/` 下执行：

```bash
python jobs/batch_industry.py
python jobs/batch_ths_full_history.py
python jobs/batch_cashflow_only.py
python jobs/fetch_consensus.py --codes 002371,300054   # 可选：指定股票
python jobs/fetch_consensus.py --dry-run                # 可选：只拉不写
```

## 注意

- `batch_industry.py` 与 `batch_ths_full_history.py` 硬编码了外部股票列表 CSV 路径 `C:\Users\achuan\Desktop\report\pdf_pipline\cn_pipeline\data\stock_list\extracted_company_data.csv`。
- `fetch_consensus.py` 依赖 `akshare`；`batch_*.py` 依赖 `requests`、`pandas`，均未在 requirements 中声明，运行时需自行安装。