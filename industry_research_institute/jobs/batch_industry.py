"""
并发批量抓取行业/板块数据，写入 vr_industry_sw 和 vr_sector_em
- 申万行业: 调用 get_10jqka_industry (同花顺)
- 东财板块: 调用 get_eastmoney_sectors (东方财富)
"""
import os
import sys
import time
import threading
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
import psycopg2.extras

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobs.fetchers.api_fetchers import get_10jqka_industry, get_eastmoney_sectors
from jobs.db_config import db_config

# ── 并发配置 ──
MAX_WORKERS = 8
THS_QPS_LIMIT = 10   # 同花顺限流
EM_QPS_LIMIT = 15    # 东财限流稍宽松

DB_CONFIG = db_config()

# ── 令牌桶限流器 ──
class RateLimiter:
    def __init__(self, rate: float):
        self.rate = rate
        self.lock = threading.Lock()
        self.last = time.monotonic()
        self.tokens = rate

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
                self.last = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
            time.sleep(1.0 / self.rate)

_ths_limiter = RateLimiter(THS_QPS_LIMIT)
_em_limiter = RateLimiter(EM_QPS_LIMIT)


def get_exchange(code: str) -> str:
    """根据股票代码判断交易所"""
    if code.startswith("6") or code.startswith("9"):
        return "1"  # 沪市
    return "0"      # 深市/北交所


def fetch_sw_industry(code: str) -> dict:
    """抓取申万行业 (带限流)"""
    _ths_limiter.acquire()
    return get_10jqka_industry(code)


def fetch_em_sectors(code: str, exchange: str) -> list:
    """抓取东财板块 (带限流)"""
    _em_limiter.acquire()
    return get_eastmoney_sectors(code, exchange)


def process_one_stock(code: str) -> dict:
    """
    并发抓取一只股票的申万行业 + 东财板块
    返回: {"sw": {...}, "em": [...]} 或 None
    """
    exchange = get_exchange(code)
    
    # 两个 API 并发调用
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_sw = pool.submit(fetch_sw_industry, code)
        f_em = pool.submit(fetch_em_sectors, code, exchange)
        
        sw_result = f_sw.result()
        em_result = f_em.result()
    
    # 判断是否有有效数据
    has_sw = sw_result and (sw_result.get("l1") or sw_result.get("l2"))
    has_em = em_result and len(em_result) > 0
    
    if not has_sw and not has_em:
        return None
    
    return {
        "code": code,
        "sw": sw_result if has_sw else None,
        "em": em_result if has_em else None,
    }


def save_to_db(results: list, db_lock: threading.Lock):
    """批量写入数据库"""
    if not results:
        return
    
    sw_tuples = []
    em_tuples = []
    
    for r in results:
        code = r["code"]
        
        # 申万行业
        if r.get("sw"):
            sw = r["sw"]
            sw_tuples.append((
                code,
                sw.get("l1"),
                sw.get("l2"),
                sw.get("raw"),
                "ths"
            ))
        
        # 东财板块
        if r.get("em"):
            for sector in r["em"]:
                # f141: 0=行业板块, 1=概念板块, 2=地域板块 (推测)
                sector_type_map = {0: "industry", 1: "concept", 2: "region"}
                sector_type = sector_type_map.get(sector.get("f141"), "unknown")
                em_tuples.append((
                    code,
                    sector.get("f12"),      # 板块代码
                    sector.get("f14"),      # 板块名称
                    sector_type,
                    sector.get("f140"),     # 领涨股代码
                ))
    
    db_lock.acquire()
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 申万行业 UPSERT
            if sw_tuples:
                sql_sw = """
                    INSERT INTO vr_industry_sw (stock_code, industry_l1, industry_l2, industry_raw, source)
                    VALUES %s
                    ON CONFLICT (stock_code) DO UPDATE SET
                        industry_l1 = EXCLUDED.industry_l1,
                        industry_l2 = EXCLUDED.industry_l2,
                        industry_raw = EXCLUDED.industry_raw,
                        source = EXCLUDED.source,
                        updated_at = CURRENT_TIMESTAMP
                """
                psycopg2.extras.execute_values(cursor, sql_sw, sw_tuples)
            
            # 东财板块: 先删后插 (一只股票可能有多条板块)
            if em_tuples:
                codes = list(set(r["code"] for r in results if r.get("em")))
                # 删除旧数据
                cursor.execute(
                    "DELETE FROM vr_sector_em WHERE stock_code = ANY(%s)",
                    (codes,)
                )
                # 插入新数据
                sql_em = """
                    INSERT INTO vr_sector_em (stock_code, sector_code, sector_name, sector_type, lead_stock_code)
                    VALUES %s
                """
                psycopg2.extras.execute_values(cursor, sql_em, em_tuples)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Error] {e}")
    finally:
        db_lock.release()


def main():
    start_time = time.monotonic()
    print(f"[{datetime.now()}] Starting Industry Data Batch (workers={MAX_WORKERS})...")
    
    # ── 断点续跑: 检查已处理的股票 ──
    already_sw = set()
    already_em = set()
    db_lock = threading.Lock()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock_code FROM vr_industry_sw")
            already_sw = {row[0] for row in cursor.fetchall()}
            cursor.execute("SELECT DISTINCT stock_code FROM vr_sector_em")
            already_em = {row[0] for row in cursor.fetchall()}
        conn.close()
        print(f"[{datetime.now()}] Already processed: SW={len(already_sw)}, EM={len(already_em)}")
    except Exception as e:
        print(f"[{datetime.now()}] Failed to check existing records: {e}")
    
    # ── 读取股票列表 ──
    csrc_path = r"C:\Users\achuan\Desktop\report\pdf_pipline\cn_pipeline\data\stock_list\extracted_company_data.csv"
    csrc_df = pd.read_csv(csrc_path)
    
    all_codes = set()
    for _, row in csrc_df.iterrows():
        code = str(row.get('上市公司代码', '')).zfill(6)
        all_codes.add(code)
    
    # 过滤掉北交所代码（8/4/9 开头）
    bj_codes = {c for c in all_codes if c.startswith('8') or c.startswith('4') or c.startswith('9')}
    all_codes -= bj_codes
    print(f"Filtered out {len(bj_codes)} 北交所 codes")
    
    # 只处理两张表都没抓过的股票
    done_codes = already_sw & already_em
    pending_codes = [c for c in all_codes if c not in done_codes]
    total = len(pending_codes)
    
    print(f"Total stocks: {len(all_codes)}, Already done: {len(done_codes)}, Remaining: {total}")
    sys.stdout.flush()
    
    if total == 0:
        print("All stocks already processed. Done!")
        return
    
    # ── 并发抓取 ──
    batch_results = []
    batch_lock = threading.Lock()
    processed_count = 0
    valid_count = 0
    skip_count = 0
    error_count = 0
    count_lock = threading.Lock()
    
    SAVE_EVERY = 100  # 每 100 只有效股票入库一次
    
    def flush_batch():
        nonlocal batch_results
        with batch_lock:
            to_save = list(batch_results)
            batch_results.clear()
        save_to_db(to_save, db_lock)
    
    def on_stock_done(future, code):
        nonlocal processed_count, valid_count, skip_count, error_count
        
        with count_lock:
            processed_count += 1
        
        try:
            result = future.result()
            if result is None:
                with count_lock:
                    skip_count += 1
                return
            
            with batch_lock:
                batch_results.append(result)
                with count_lock:
                    valid_count += 1
                    cur_valid = valid_count
        except Exception as e:
            with count_lock:
                error_count += 1
            print(f"[{datetime.now()}] [{code}] Error: {e}")
            return
        
        with count_lock:
            cur_processed = processed_count
            cur_skip = skip_count
            cur_err = error_count
        
        # 进度日志
        if cur_processed % 100 == 0:
            elapsed = time.monotonic() - start_time
            rate = cur_processed / elapsed if elapsed > 0 else 0
            eta_s = (total - cur_processed) / rate if rate > 0 else 0
            print(f"[{datetime.now()}] Progress: {cur_processed}/{total} "
                  f"({cur_processed/total*100:.1f}%) | "
                  f"valid={cur_valid} skip={cur_skip} err={cur_err} | "
                  f"{rate:.1f} stocks/s | ETA {eta_s/60:.0f}min")
            sys.stdout.flush()
        
        # 批量入库
        if cur_valid > 0 and cur_valid % SAVE_EVERY == 0:
            flush_batch()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for code in pending_codes:
            fut = executor.submit(process_one_stock, code)
            futures[fut] = code
            fut.add_done_callback(lambda f, c=code: on_stock_done(f, c))
        
        for fut in as_completed(futures):
            pass
    
    # 最终入库
    flush_batch()
    
    elapsed = time.monotonic() - start_time
    print(f"\n[{datetime.now()}] Industry batch completed in {elapsed/60:.1f} min")
    print(f"  Processed: {processed_count} | Valid: {valid_count} | "
          f"Skipped: {skip_count} | Errors: {error_count}")


if __name__ == "__main__":
    main()
