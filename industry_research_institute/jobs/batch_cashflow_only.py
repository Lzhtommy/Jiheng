"""
THS 现金流量表补抓脚本
仅为已有 main/debt/benefit 但缺少 cashflow 的股票补抓现金流量表数据
"""
import os
import sys
import time
import json
import threading
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
import psycopg2.extras

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobs.db_config import db_config

from jobs.batch_ths_full_history import (
    fetch_ths_finance, safe_float, CASH_METRICS, RateLimiter
)

# ── Config ──
MAX_STOCK_WORKERS = 8
THS_QPS_LIMIT = 12

DB_CONFIG = db_config()

H_THS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://basic.10jqka.com.cn/",
}

_ths_limiter = RateLimiter(THS_QPS_LIMIT)


def fetch_cash_only(code: str, session: requests.Session) -> dict:
    """Only fetch cash flow data for one stock"""
    _ths_limiter.acquire()
    url = f"https://basic.10jqka.com.cn/api/stock/finance/{code}_cash.json"
    headers = H_THS.copy()
    headers["Referer"] = f"https://basic.10jqka.com.cn/{code}/finance.html"
    try:
        r = session.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "flashData" in data:
            flash = json.loads(data["flashData"])
            dates = flash['report'][0]
            metrics = [t[0] for t in flash['title'][1:]]
            parsed = {d: {} for d in dates if d}
            for i, row in enumerate(flash['report'][1:]):
                metric_name = metrics[i]
                for j, date_val in enumerate(dates):
                    if not date_val:
                        continue
                    val = row[j]
                    if isinstance(val, str):
                        if '亿' in val:
                            try:
                                val = float(val.replace('亿', '')) * 100000000
                            except:
                                val = None
                        elif '万' in val:
                            try:
                                val = float(val.replace('万', '')) * 10000
                            except:
                                val = None
                        elif '%' in val:
                            try:
                                val = float(val.replace('%', '')) / 100
                            except:
                                val = None
                        else:
                            try:
                                val = float(val)
                            except:
                                val = None
                    parsed[date_val][metric_name] = val
            return parsed
    except Exception:
        pass
    return {}


def save_cash_batch(all_stocks_data: list):
    """Batch save cashflow data only"""
    if not all_stocks_data:
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cash_rows = []
        for stock_code, cash_data in all_stocks_data:
            if cash_data:
                for period, metrics in cash_data.items():
                    row = [stock_code, period]
                    for cn_name, en_name in CASH_METRICS.items():
                        row.append(safe_float(metrics.get(cn_name)))
                    cash_rows.append(row)

        if cash_rows:
            cols = ['stock_code', 'report_period'] + list(CASH_METRICS.values())
            col_names = ', '.join(cols)
            sql = f"""
                INSERT INTO vr_ths_cashflow ({col_names})
                VALUES %s
                ON CONFLICT (stock_code, report_period) DO UPDATE SET
                {', '.join([f"{c} = EXCLUDED.{c}" for c in cols[2:]])}
            """
            psycopg2.extras.execute_values(cur, sql, cash_rows, page_size=1000)
            print(f"  Inserted {len(cash_rows)} cashflow records")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
    finally:
        cur.close()
        conn.close()


def main():
    start_time = time.monotonic()
    print(f"[{datetime.now()}] Starting Cash Flow Data Backfill...")
    print(f"Workers: {MAX_STOCK_WORKERS}, THS QPS: {THS_QPS_LIMIT}")

    # Load stock list
    csrc_path = r"C:\Users\achuan\Desktop\report\pdf_pipline\cn_pipeline\data\stock_list\extracted_company_data.csv"
    csrc_df = pd.read_csv(csrc_path)

    codes = []
    for _, row in csrc_df.iterrows():
        code = str(row.get('上市公司代码', '')).zfill(6)
        # Filter out BSE stocks
        if code.startswith('4') or code.startswith('8'):
            continue
        codes.append(code)

    total = len(codes)
    print(f"Total stocks: {total}")
    sys.stdout.flush()

    # Check which stocks already have cashflow data
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT stock_code FROM vr_ths_cashflow")
        already_done = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()

        pending_codes = [c for c in codes if c not in already_done]
        print(f"Already have cashflow: {len(already_done)}, Remaining: {len(pending_codes)}")
    except Exception as e:
        print(f"Failed to check existing data: {e}")
        pending_codes = codes

    if not pending_codes:
        print("All stocks already have cashflow data!")
        return

    sys.stdout.flush()

    # Processing
    processed_count = 0
    success_count = 0
    error_count = 0
    count_lock = threading.Lock()

    batch_results = []
    batch_lock = threading.Lock()
    SAVE_EVERY = 100

    thread_local = threading.local()

    def get_session():
        if not hasattr(thread_local, 'session'):
            thread_local.session = requests.Session()
        return thread_local.session

    def flush_batch():
        nonlocal batch_results
        with batch_lock:
            to_save = list(batch_results)
            batch_results.clear()
        if to_save:
            save_cash_batch(to_save)

    def on_stock_done(future, code):
        nonlocal processed_count, success_count, error_count

        with count_lock:
            processed_count += 1

        try:
            cash_data = future.result()
            cash_count = len(cash_data) if cash_data else 0
            cur_valid = 0
            if cash_count > 0:
                with batch_lock:
                    batch_results.append((code, cash_data))
                with count_lock:
                    success_count += 1
                    cur_valid = len(batch_results)
            else:
                with count_lock:
                    error_count += 1
        except Exception as e:
            with count_lock:
                error_count += 1
            print(f"[{datetime.now()}] [{code}] Error: {e}")
            return

        # Progress log
        with count_lock:
            cur_processed = processed_count
            cur_success = success_count

        if cur_processed % 50 == 0:
            elapsed = time.monotonic() - start_time
            rate = cur_processed / elapsed if elapsed > 0 else 0
            eta_s = (len(pending_codes) - cur_processed) / rate if rate > 0 else 0
            print(f"[{datetime.now()}] Progress: {cur_processed}/{len(pending_codes)} "
                  f"({cur_processed/len(pending_codes)*100:.1f}%) | "
                  f"success={cur_success} err={error_count} | "
                  f"{rate:.2f} stocks/s | ETA {eta_s/60:.0f}min")
            sys.stdout.flush()

        # Flush batch to DB
        if cur_valid > 0 and cur_valid % SAVE_EVERY == 0:
            flush_batch()

    # Main concurrent loop
    with ThreadPoolExecutor(max_workers=MAX_STOCK_WORKERS) as executor:
        futures = {}
        for code in pending_codes:
            session = get_session()
            fut = executor.submit(fetch_cash_only, code, session)
            futures[fut] = code
            fut.add_done_callback(lambda f, c=code: on_stock_done(f, c))

        for fut in as_completed(futures):
            pass

    # Final flush
    flush_batch()

    elapsed = time.monotonic() - start_time
    print(f"\n[{datetime.now()}] Batch completed in {elapsed/60:.1f} min")
    print(f"Processed: {processed_count} | Success: {success_count} | Errors: {error_count}")


if __name__ == "__main__":
    main()
