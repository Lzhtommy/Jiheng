"""
一致预期数据拉取 + 融合作业

流程:
1. 从同花顺 / 东财拉取原始一致预期数据
2. 写入 vr_consensus_source（原样入库）
3. 按融合规则生成 vr_consensus_snapshot（EPS/净利以 THS 为准，评级/目标价用 EM 补）
4. 双源 EPS 差异超阈值时设 conflict_flag

使用:
  python jobs/fetch_consensus.py                    # 全市场（从 vr_ths_main 取股票列表）
  python jobs/fetch_consensus.py --codes 600519,000858
  python jobs/fetch_consensus.py --codes 600519 --dry-run   # 只拉取不入库
"""
import os
import sys
import time
import json
import logging
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

import psycopg2
import psycopg2.extras
import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobs.db_config import db_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_CONFIG = db_config()

# ── 限流 ──
FETCH_INTERVAL = 0.5  # 每次请求间隔秒数（同花顺/东财单票接口）
CONFLICT_THRESHOLD = 0.10  # 双源 EPS 相对差超过 10% 则 conflict_flag
MAX_WORKERS = 15  # 并发线程数

_throttle_ths_last = 0.0
_throttle_em_last = 0.0
_ths_lock = threading.Lock()
_em_lock = threading.Lock()


def _throttle_ths():
    """THS 源限流，每次 API 调用前调用"""
    global _throttle_ths_last
    with _ths_lock:
        now = time.monotonic()
        wait = FETCH_INTERVAL - (now - _throttle_ths_last)
        if wait > 0:
            time.sleep(wait)
        _throttle_ths_last = time.monotonic()


def _throttle_em():
    """EM 源限流，每次 API 调用前调用"""
    global _throttle_em_last
    with _em_lock:
        now = time.monotonic()
        wait = FETCH_INTERVAL - (now - _throttle_em_last)
        if wait > 0:
            time.sleep(wait)
        _throttle_em_last = time.monotonic()


# ══════════════════════════════════════════════════
#  P0-1: 同花顺 F10 盈利预测
# ══════════════════════════════════════════════════

def fetch_ths_consensus(code: str) -> Optional[Dict]:
    """
    从同花顺 F10 拉取一致预期。返回 dict 或 None（无覆盖）。
    字段: fy1/2/3_year, fy1/2/3_eps, fy1_eps_min/max,
          fy1/2/3_np (元), fy1_revenue/bps/roe,
          coverage, latest_report_date
    """
    import akshare as ak

    _throttle_ths()
    try:
        eps_df = ak.stock_profit_forecast_ths(code, indicator="预测年报每股收益")
    except Exception as e:
        logging.warning("THS EPS failed for %s: %s", code, e)
        return None

    if eps_df is None or eps_df.empty:
        return None

    result: Dict[str, Any] = {}

    # EPS
    for i, prefix in enumerate(["fy1", "fy2", "fy3"]):
        if i < len(eps_df):
            row = eps_df.iloc[i]
            result[f"{prefix}_year"] = int(row["年度"])
            result[f"{prefix}_eps"] = _safe_float(row.get("均值"))
            if prefix == "fy1":
                result["fy1_eps_min"] = _safe_float(row.get("最小值"))
                result["fy1_eps_max"] = _safe_float(row.get("最大值"))
                result["coverage"] = _safe_int(row.get("预测机构数"))

    # 无覆盖则早退出，省去后续 3 次 API 调用
    if not result.get("coverage"):
        return None

    # 净利润
    _throttle_ths()
    try:
        np_df = ak.stock_profit_forecast_ths(code, indicator="预测年报净利润")
        if np_df is not None and not np_df.empty:
            for i, prefix in enumerate(["fy1", "fy2", "fy3"]):
                if i < len(np_df):
                    val = _safe_float(np_df.iloc[i].get("均值"))
                    # 同花顺返回的是亿元，转换为元
                    result[f"{prefix}_np"] = val * 1e8 if val is not None else None
    except Exception as e:
        logging.warning("THS net_profit failed for %s: %s", code, e)

    # 详细指标预测 (DCF/RIM)
    _throttle_ths()
    try:
        detail_df = ak.stock_profit_forecast_ths(code, indicator="业绩预测详表-详细指标预测")
        if detail_df is not None and not detail_df.empty:
            result["extra_detail"] = _parse_ths_detail(detail_df)
    except Exception as e:
        logging.warning("THS detail failed for %s: %s", code, e)

    # 机构详表 → latest_report_date
    _throttle_ths()
    try:
        inst_df = ak.stock_profit_forecast_ths(code, indicator="业绩预测详表-机构")
        if inst_df is not None and not inst_df.empty and "报告日期" in inst_df.columns:
            dates = pd.to_datetime(inst_df["报告日期"], errors="coerce").dropna()
            if not dates.empty:
                result["latest_report_date"] = dates.max().date()
    except Exception as e:
        logging.warning("THS inst failed for %s: %s", code, e)

    return result if result else None


def _parse_ths_detail(detail_df: pd.DataFrame) -> Dict:
    """解析同花顺详细指标预测表，提取 DCF/RIM 可用字段"""
    extra = {}
    # 查找包含 "营业收入" / "每股净资产" / "净资产收益率" 的行
    for _, row in detail_df.iterrows():
        indicator = str(row.get("预测指标", ""))
        # 尝试各个预测年份列
        for col in row.index:
            if "预测" in str(col) and "平均" in str(col):
                val_str = str(row[col]).replace("亿", "").replace("%", "").strip()
                try:
                    val = float(val_str)
                except (ValueError, TypeError):
                    continue
                if "营业收入" in indicator:
                    extra[f"revenue_{col}"] = val
                elif "每股净资产" in indicator:
                    extra[f"bps_{col}"] = val
                elif "净资产收益率" in indicator:
                    extra[f"roe_{col}"] = val
    return extra


# ══════════════════════════════════════════════════
#  P0-2: 东财一致预期 JSON
# ══════════════════════════════════════════════════

def fetch_em_consensus(code: str) -> Optional[Dict]:
    """
    从东财 RPT_WEB_RESPREDICT 拉取一致预期（直连，不走 AKShare，保留目标价）。
    """
    _throttle_em()
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_WEB_RESPREDICT",
        "columns": "WEB_RESPREDICT",
        "pageNumber": "1",
        "pageSize": "1",
        "sortTypes": "-1",
        "sortColumns": "RATING_ORG_NUM",
        "filter": f'(SECURITY_CODE="{code}")',
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        j = r.json()
    except Exception as e:
        logging.warning("EM consensus failed for %s: %s", code, e)
        return None

    if not j.get("result") or not j["result"].get("data"):
        return None

    row = j["result"]["data"][0]

    # 解析 EPS: 只取预测年份 (YEAR_MARKn == 'E')
    eps_by_year = {}
    for i in range(1, 5):
        mark = row.get(f"YEAR_MARK{i}")
        year = row.get(f"YEAR{i}")
        eps_val = row.get(f"EPS{i}")
        if mark == "E" and eps_val is not None:
            eps_by_year[year] = float(eps_val)

    # 按年份排序取 FY1/2/3
    sorted_years = sorted(eps_by_year.keys())
    result: Dict[str, Any] = {}
    for i, prefix in enumerate(["fy1", "fy2", "fy3"]):
        if i < len(sorted_years):
            year = sorted_years[i]
            result[f"{prefix}_year"] = int(year)
            result[f"{prefix}_eps"] = eps_by_year[year]

    result["coverage"] = _safe_int(row.get("RATING_ORG_NUM"))
    result["rating_buy"] = _safe_int(row.get("RATING_BUY_NUM"))
    result["rating_add"] = _safe_int(row.get("RATING_ADD_NUM"))
    result["rating_hold"] = _safe_int(row.get("RATING_NEUTRAL_NUM"))
    result["rating_reduce"] = _safe_int(row.get("RATING_REDUCE_NUM"))
    result["rating_sell"] = _safe_int(row.get("RATING_SALE_NUM"))
    result["target_high"] = _safe_float(row.get("DEC_AIMPRICEMAX"))
    result["target_low"] = _safe_float(row.get("DEC_AIMPRICEMIN"))

    return result if result else None


# ══════════════════════════════════════════════════
#  融合规则
# ══════════════════════════════════════════════════

def merge_consensus(
    ths: Optional[Dict],
    em: Optional[Dict],
    batch_date: date,
    ttm_net_income: Optional[float] = None,
) -> Dict:
    """
    融合规则（写死、可测）:
    - EPS / 净利 / 覆盖 / 新鲜度 以同花顺为准
    - 评级和目标价区间用东财补
    - 双源 EPS 相对差超过阈值则 conflict_flag=True

    返回适合写入 vr_consensus_snapshot 的 dict。
    """
    snap: Dict[str, Any] = {
        "batch_date": batch_date,
        "primary_source": None,
        "backup_source": None,
        "conflict_flag": False,
    }

    # ── EPS / 净利 / 覆盖 / 新鲜度: THS 优先 ──
    if ths:
        snap["primary_source"] = "ths"
        snap["fy1_eps"] = ths.get("fy1_eps")
        snap["fy2_eps"] = ths.get("fy2_eps")
        snap["fy3_eps"] = ths.get("fy3_eps")
        snap["fy1_net_income"] = ths.get("fy1_np")
        snap["coverage"] = ths.get("coverage")

        # freshness_days
        latest = ths.get("latest_report_date")
        if latest:
            snap["freshness_days"] = (batch_date - latest).days
        else:
            snap["freshness_days"] = None
    elif em:
        # THS 缺失，降级用 EM
        snap["primary_source"] = "em"
        snap["fy1_eps"] = em.get("fy1_eps")
        snap["fy2_eps"] = em.get("fy2_eps")
        snap["fy3_eps"] = em.get("fy3_eps")
        snap["fy1_net_income"] = None  # 东财无净利
        snap["coverage"] = em.get("coverage")
        snap["freshness_days"] = None  # 东财无研报日期

    # ── fy1_growth: FY1 净利相对 TTM 的增速 ──
    fy1_np = snap.get("fy1_net_income")
    if fy1_np and ttm_net_income and ttm_net_income > 0:
        snap["fy1_growth"] = (fy1_np - ttm_net_income) / abs(ttm_net_income)
    else:
        snap["fy1_growth"] = None

    # ── 评级 / 目标价: EM 优先 ──
    if em:
        if snap["primary_source"] != "em":
            snap["backup_source"] = "em"
        snap["rating_buy"] = em.get("rating_buy")
        snap["rating_add"] = em.get("rating_add")
        snap["rating_hold"] = em.get("rating_hold")
        snap["rating_reduce"] = em.get("rating_reduce")
        snap["rating_sell"] = em.get("rating_sell")
        snap["target_high"] = em.get("target_high")
        snap["target_low"] = em.get("target_low")

    # ── conflict_flag: 双源 EPS 差异检查 ──
    if ths and em:
        ths_eps = ths.get("fy1_eps")
        em_eps = em.get("fy1_eps")
        if ths_eps and em_eps and max(ths_eps, em_eps) > 0:
            diff = abs(ths_eps - em_eps) / max(ths_eps, em_eps)
            if diff > CONFLICT_THRESHOLD:
                snap["conflict_flag"] = True
                logging.warning(
                    "conflict_flag: EPS diff %.2f%% (ths=%.4f em=%.4f)",
                    diff * 100, ths_eps, em_eps,
                )

    return snap


# ══════════════════════════════════════════════════
#  入库
# ══════════════════════════════════════════════════

def upsert_source(cur, as_of: date, stock_code: str, source: str, data: Dict):
    """写入 vr_consensus_source（UPSERT）"""
    # 把 extra_detail 放进 extra JSONB
    extra = {}
    if "extra_detail" in data:
        extra = data.pop("extra_detail")

    cur.execute("""
        INSERT INTO vr_consensus_source (
            as_of, stock_code, source,
            fy1_year, fy2_year, fy3_year,
            fy1_eps, fy2_eps, fy3_eps,
            fy1_eps_min, fy1_eps_max,
            fy1_np, fy2_np, fy3_np,
            fy1_revenue, fy1_bps, fy1_roe,
            coverage,
            rating_buy, rating_add, rating_hold, rating_reduce, rating_sell,
            target_high, target_low, target_median,
            latest_report_date,
            fetched_at, extra
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s,
            %s, %s
        )
        ON CONFLICT (as_of, stock_code, source) DO UPDATE SET
            fy1_year = EXCLUDED.fy1_year,
            fy2_year = EXCLUDED.fy2_year,
            fy3_year = EXCLUDED.fy3_year,
            fy1_eps = EXCLUDED.fy1_eps,
            fy2_eps = EXCLUDED.fy2_eps,
            fy3_eps = EXCLUDED.fy3_eps,
            fy1_eps_min = EXCLUDED.fy1_eps_min,
            fy1_eps_max = EXCLUDED.fy1_eps_max,
            fy1_np = EXCLUDED.fy1_np,
            fy2_np = EXCLUDED.fy2_np,
            fy3_np = EXCLUDED.fy3_np,
            fy1_revenue = EXCLUDED.fy1_revenue,
            fy1_bps = EXCLUDED.fy1_bps,
            fy1_roe = EXCLUDED.fy1_roe,
            coverage = EXCLUDED.coverage,
            rating_buy = EXCLUDED.rating_buy,
            rating_add = EXCLUDED.rating_add,
            rating_hold = EXCLUDED.rating_hold,
            rating_reduce = EXCLUDED.rating_reduce,
            rating_sell = EXCLUDED.rating_sell,
            target_high = EXCLUDED.target_high,
            target_low = EXCLUDED.target_low,
            target_median = EXCLUDED.target_median,
            latest_report_date = EXCLUDED.latest_report_date,
            fetched_at = EXCLUDED.fetched_at,
            extra = EXCLUDED.extra
    """, (
        as_of, stock_code, source,
        data.get("fy1_year"), data.get("fy2_year"), data.get("fy3_year"),
        data.get("fy1_eps"), data.get("fy2_eps"), data.get("fy3_eps"),
        data.get("fy1_eps_min"), data.get("fy1_eps_max"),
        data.get("fy1_np"), data.get("fy2_np"), data.get("fy3_np"),
        data.get("fy1_revenue"), data.get("fy1_bps"), data.get("fy1_roe"),
        data.get("coverage"),
        data.get("rating_buy"), data.get("rating_add"), data.get("rating_hold"),
        data.get("rating_reduce"), data.get("rating_sell"),
        data.get("target_high"), data.get("target_low"), data.get("target_median"),
        data.get("latest_report_date"),
        datetime.now(),
        json.dumps(extra, ensure_ascii=False, default=str) if extra else None,
    ))


def upsert_snapshot(cur, stock_code: str, snap: Dict):
    """写入 vr_consensus_snapshot（UPSERT）"""
    cur.execute("""
        INSERT INTO vr_consensus_snapshot (
            batch_date, stock_code,
            fy1_eps, fy1_net_income, fy1_growth,
            fy2_eps, fy3_eps,
            coverage, freshness_days,
            rating_buy, rating_add, rating_hold, rating_reduce, rating_sell,
            target_high, target_low,
            primary_source, backup_source, conflict_flag
        ) VALUES (
            %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (batch_date, stock_code) DO UPDATE SET
            fy1_eps = EXCLUDED.fy1_eps,
            fy1_net_income = EXCLUDED.fy1_net_income,
            fy1_growth = EXCLUDED.fy1_growth,
            fy2_eps = EXCLUDED.fy2_eps,
            fy3_eps = EXCLUDED.fy3_eps,
            coverage = EXCLUDED.coverage,
            freshness_days = EXCLUDED.freshness_days,
            rating_buy = EXCLUDED.rating_buy,
            rating_add = EXCLUDED.rating_add,
            rating_hold = EXCLUDED.rating_hold,
            rating_reduce = EXCLUDED.rating_reduce,
            rating_sell = EXCLUDED.rating_sell,
            target_high = EXCLUDED.target_high,
            target_low = EXCLUDED.target_low,
            primary_source = EXCLUDED.primary_source,
            backup_source = EXCLUDED.backup_source,
            conflict_flag = EXCLUDED.conflict_flag
    """, (
        snap["batch_date"], stock_code,
        snap.get("fy1_eps"), snap.get("fy1_net_income"), snap.get("fy1_growth"),
        snap.get("fy2_eps"), snap.get("fy3_eps"),
        snap.get("coverage"), snap.get("freshness_days"),
        snap.get("rating_buy"), snap.get("rating_add"), snap.get("rating_hold"),
        snap.get("rating_reduce"), snap.get("rating_sell"),
        snap.get("target_high"), snap.get("target_low"),
        snap.get("primary_source"), snap.get("backup_source"), snap.get("conflict_flag"),
    ))


# ══════════════════════════════════════════════════
#  辅助
# ══════════════════════════════════════════════════

def _safe_float(val) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def get_stock_codes(conn, target_codes: Optional[List[str]] = None) -> List[str]:
    """获取股票列表（复用 batch_route_v2 的逻辑）"""
    with conn.cursor() as cur:
        if target_codes:
            placeholders = ','.join(['%s'] * len(target_codes))
            cur.execute(
                f"SELECT DISTINCT stock_code FROM vr_ths_main WHERE stock_code IN ({placeholders})",
                tuple(target_codes),
            )
        else:
            cur.execute("SELECT DISTINCT stock_code FROM vr_ths_main")
        codes = [r[0] for r in cur.fetchall()]

    # 过滤北交所
    return [c for c in codes if not (c.startswith('4') or c.startswith('8'))]


def get_ttm_net_income(conn, codes: List[str]) -> Dict[str, float]:
    """从 vr_ths_main 取最近一期年报净利润，用于算 fy1_growth"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (stock_code) stock_code, net_income
            FROM vr_ths_main
            WHERE stock_code = ANY(%s)
              AND EXTRACT(MONTH FROM report_period) = 12
              AND net_income IS NOT NULL
            ORDER BY stock_code, report_period DESC
        """, (codes,))
        return {r[0]: float(r[1]) for r in cur.fetchall()}


def get_already_fetched(conn, as_of: date, codes: List[str]) -> set:
    """查询今天已经拉过的股票（source 表主键含 source，这里查有无任何 source 的记录）"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT stock_code FROM vr_consensus_source
            WHERE as_of = %s AND stock_code = ANY(%s)
        """, (as_of, codes))
        return {r[0] for r in cur.fetchall()}


# ══════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════

def process_stock(code, skip_ths, skip_em, dry_run, ttm_map):
    """处理单只股票：并发拉取双源 + 融合 + 入库，返回 (status, code)"""
    ths_data = None
    em_data = None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        if not skip_ths:
            futures['ths'] = pool.submit(fetch_ths_consensus, code)
        if not skip_em:
            futures['em'] = pool.submit(fetch_em_consensus, code)

        for key, fut in futures.items():
            try:
                result = fut.result()
                if key == 'ths':
                    ths_data = result
                else:
                    em_data = result
            except Exception as e:
                logging.error("  %s error for %s: %s", key.upper(), code, e)

    if ths_data:
        logging.info("  [%s] THS: coverage=%s, fy1_eps=%s",
                     code, ths_data.get("coverage"), ths_data.get("fy1_eps"))
    elif not skip_ths:
        logging.info("  [%s] THS: no coverage", code)

    if em_data:
        logging.info("  [%s] EM:  coverage=%s, fy1_eps=%s, target=%s~%s",
                     code, em_data.get("coverage"), em_data.get("fy1_eps"),
                     em_data.get("target_low"), em_data.get("target_high"))
    elif not skip_em:
        logging.info("  [%s] EM:  no coverage", code)

    if not ths_data and not em_data:
        return ("skip", code)

    snap = merge_consensus(
        ths_data, em_data,
        batch_date=date.today(),
        ttm_net_income=ttm_map.get(code),
    )

    if dry_run:
        logging.info("  [%s] [DRY-RUN] snapshot: %s", code, json.dumps(
            {k: str(v) if isinstance(v, (date, Decimal)) else v for k, v in snap.items()},
            ensure_ascii=False,
        ))
        return ("ok", code)

    try:
        thread_conn = psycopg2.connect(**DB_CONFIG)
        try:
            with thread_conn.cursor() as cur:
                if ths_data:
                    upsert_source(cur, date.today(), code, "ths", ths_data)
                if em_data:
                    upsert_source(cur, date.today(), code, "em", em_data)
                upsert_snapshot(cur, code, snap)
            thread_conn.commit()
        except Exception as e:
            thread_conn.rollback()
            logging.error("  [%s] DB error: %s", code, e)
            return ("fail", code)
        finally:
            thread_conn.close()
        return ("ok", code)
    except Exception as e:
        logging.error("  [%s] Connection error: %s", code, e)
        return ("fail", code)


def main():
    parser = argparse.ArgumentParser(description="Fetch consensus estimates")
    parser.add_argument("--codes", type=str, help="Comma-separated stock codes")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only, don't write to DB")
    parser.add_argument("--skip-ths", action="store_true", help="Skip THS (only fetch EM)")
    parser.add_argument("--skip-em", action="store_true", help="Skip EM (only fetch THS)")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already done today")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    today = date.today()

    target_codes = args.codes.split(",") if args.codes else None
    codes = get_stock_codes(conn, target_codes)
    logging.info("Total codes: %d", len(codes))

    # 跳过今天已拉取的
    if not args.force:
        already = get_already_fetched(conn, today, codes)
        codes = [c for c in codes if c not in already]
        logging.info("After skipping already fetched: %d", len(codes))

    if not codes:
        logging.info("Nothing to fetch.")
        conn.close()
        return

    # 取 TTM 净利润（用于 fy1_growth）
    ttm_map = get_ttm_net_income(conn, codes)
    conn.close()  # 主连接关闭，工作线程各自建连接

    ok = 0
    fail = 0
    skip = 0
    total = len(codes)

    logging.info("Starting fetch with %d workers ...", MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_code = {
            executor.submit(
                process_stock, code,
                args.skip_ths, args.skip_em, args.dry_run, ttm_map,
            ): code
            for code in codes
        }
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            done = ok + fail + skip + 1
            try:
                status, _ = future.result()
                if status == "ok":
                    ok += 1
                elif status == "fail":
                    fail += 1
                else:
                    skip += 1
                if status != "skip":
                    logging.info("[%d/%d] %s -> %s (ok=%d fail=%d skip=%d)",
                                 done, total, code, status, ok, fail, skip)
            except Exception as e:
                fail += 1
                logging.error("[%d/%d] %s -> ERROR: %s", done, total, code, e)

    logging.info("Done. ok=%d, fail=%d, skip=%d, total=%d", ok, fail, skip, total)


if __name__ == "__main__":
    main()
