"""
THS 全量历史财务数据提取脚本
提取所有股票从上市至今的全部历史财报数据
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

# ── Config ──
MAX_STOCK_WORKERS = 8
THS_QPS_LIMIT = 12

DB_CONFIG = db_config()

H_THS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://basic.10jqka.com.cn/",
}

# ── Rate Limiter ──
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

# ── THS Metric Name Mapping ──
# main table metrics
MAIN_METRICS = {
    '净利润': 'net_income',
    '净利润同比增长率': 'net_income_yoy',
    '扣非净利润': 'deducted_net_income',
    '扣非净利润同比增长率': 'deducted_net_income_yoy',
    '营业总收入': 'revenue',
    '营业总收入同比增长率': 'revenue_yoy',
    '基本每股收益': 'eps',
    '每股净资产': 'bps',
    '每股资本公积金': 'capital_reserve_per_share',
    '每股未分配利润': 'undistributed_profit_per_share',
    '每股经营现金流': 'ocf_per_share',
    '销售净利率': 'net_profit_margin',
    '销售毛利率': 'gross_profit_margin',
    '净资产收益率': 'roe',
    '净资产收益率-摊薄': 'roe_diluted',
    '营业周期': 'operating_cycle',
    '存货周转率': 'inventory_turnover',
    '存货周转天数': 'inventory_turnover_days',
    '应收账款周转天数': 'ar_turnover_days',
    '流动比率': 'current_ratio',
    '速动比率': 'quick_ratio',
    '保守速动比率': 'conservative_quick_ratio',
    '产权比率': 'debt_to_equity',
    '资产负债率': 'debt_ratio',
}

# debt table metrics
DEBT_METRICS = {
    '*资产合计': 'total_assets',
    '*负债合计': 'total_liabilities',
    '*所有者权益（或股东权益）合计': 'total_equity',
    '*归属于母公司所有者权益合计': 'equity_to_parent',
    '流动资产': 'current_assets',
    '货币资金': 'cash',
    '交易性金融资产': 'trading_financial_assets',
    '应收账款': 'ar',
    '应收票据': 'notes_receivable',
    '预付款项': 'prepayments',
    '其他应收款合计': 'other_receivables',
    '存货': 'inventory',
    '其他流动资产': 'other_current_assets',
    '非流动资产合计': 'non_current_assets',
    '可供出售金融资产': 'available_for_sale_financial_assets',
    '长期股权投资': 'long_term_equity_investment',
    '投资性房地产': 'investment_property',
    '固定资产合计': 'fixed_assets',
    '在建工程合计': 'construction_in_progress',
    '无形资产': 'intangible_assets',
    '商誉': 'goodwill',
    '长期待摊费用': 'long_term_prepaid_expenses',
    '递延所得税资产': 'deferred_tax_assets',
    '其他非流动资产': 'other_non_current_assets',
    '流动负债合计': 'current_liabilities',
    '短期借款': 'short_term_borrowings',
    '应付票据': 'notes_payable',
    '应付账款': 'accounts_payable',
    '预收款项': 'advance_receipts',
    '合同负债': 'contract_liabilities',
    '应付职工薪酬': 'employee_compensation',
    '应交税费': 'taxes_payable',
    '其他应付款合计': 'other_payables',
    '一年内到期的非流动负债': 'current_portion_of_non_current_liabilities',
    '其他流动负债': 'other_current_liabilities',
    '非流动负债合计': 'non_current_liabilities',
    '长期借款': 'long_term_borrowings',
    '应付债券': 'bonds_payable',
    '长期应付款合计': 'long_term_payables',
    '递延所得税负债': 'deferred_tax_liabilities',
    '递延收益-非流动负债': 'deferred_revenue_non_current',
    '其他非流动负债': 'other_non_current_liabilities',
    '实收资本（或股本）': 'paid_in_capital',
    '资本公积': 'capital_reserve',
    '减：库存股': 'treasury_stock',
    '其他综合收益': 'other_comprehensive_income',
    '盈余公积': 'surplus_reserve',
    '未分配利润': 'undistributed_profit',
    '少数股东权益': 'minority_interest',
}

# benefit table metrics
BENEFIT_METRICS = {
    '*净利润': 'net_income',
    '*营业总收入': 'revenue',
    '*营业总成本': 'total_cost',
    '*归属于母公司所有者的净利润': 'net_income_to_parent',
    '*扣除非经常性损益后的净利润': 'deducted_net_income',
    '营业收入': 'operating_revenue',
    '营业成本': 'operating_cost',
    '营业税金及附加': 'business_tax_and_surcharges',
    '销售费用': 'selling_expenses',
    '管理费用': 'administrative_expenses',
    '研发费用': 'rd_expenses',
    '财务费用': 'financial_expenses',
    '利息费用': 'interest_expense',
    '利息收入': 'interest_income',
    '资产减值损失': 'asset_impairment_loss',
    '信用减值损失': 'credit_impairment_loss',
    '公允价值变动收益': 'fair_value_change_income',
    '投资收益': 'investment_income',
    '联营企业和合营企业的投资收益': 'investment_income_from_associates',
    '资产处置收益': 'asset_disposal_income',
    '其他收益': 'other_income',
    '营业利润': 'operating_profit',
    '营业外收入': 'non_operating_income',
    '营业外支出': 'non_operating_expense',
    '利润总额': 'total_profit',
    '所得税费用': 'income_tax_expense',
    '持续经营净利润': 'continuing_operations_net_income',
    '少数股东损益': 'minority_profit',
    '基本每股收益': 'basic_eps',
    '稀释每股收益': 'diluted_eps',
    '其他综合收益': 'other_comprehensive_income',
    '归属母公司所有者的其他综合收益': 'oci_to_parent',
    '综合收益总额': 'total_comprehensive_income',
    '归属于母公司股东的综合收益总额': 'comprehensive_income_to_parent',
    '归属于少数股东的综合收益总额': 'comprehensive_income_to_minority',
}

# cashflow table metrics
CASH_METRICS = {
    # 核心指标
    '*现金及现金等价物净增加额': 'net_cash_increase',
    '*经营活动产生的现金流量净额': 'net_cashflow_from_operate',
    '*投资活动产生的现金流量净额': 'net_cashflow_from_invest',
    '*筹资活动产生的现金流量净额': 'net_cashflow_from_finance',
    '*期末现金及现金等价物余额': 'cash_end_period',
    '加：期初现金及现金等价物余额': 'cash_begin_period',
    # 经营活动明细
    '销售商品、提供劳务收到的现金': 'sales_rendered_cash',
    '收到的税费与返还': 'tax_refund',
    '收到其他与经营活动有关的现金': 'other_cash_operate_in',
    '经营活动现金流入小计': 'total_cash_operate_in',
    '购买商品、接受劳务支付的现金': 'buy_goods_services_cash',
    '支付给职工以及为职工支付的现金': 'employee_compensation_cash',
    '支付的各项税费': 'tax_paid',
    '支付其他与经营活动有关的现金': 'other_cash_operate_out',
    '经营活动现金流出小计': 'total_cash_operate_out',
    # 投资活动明细
    '收回投资收到的现金': 'withdraw_invest_cash',
    '取得投资收益收到的现金': 'invest_income_cash',
    '处置固定资产、无形资产和其他长期资产收回的现金净额': 'dispose_fixed_asset_cash',
    '收到其他与投资活动有关的现金': 'other_cash_invest_in',
    '投资活动现金流入小计': 'total_cash_invest_in',
    '购建固定资产、无形资产和其他长期资产支付的现金': 'acquire_fixed_asset_cash',
    '投资支付的现金': 'invest_paid_cash',
    '支付其他与投资活动有关的现金': 'other_cash_invest_out',
    '投资活动现金流出小计': 'total_cash_invest_out',
    # 筹资活动明细
    '吸收投资收到的现金': 'absorb_invest_cash',
    '取得借款收到的现金': 'loan_received_cash',
    '收到其他与筹资活动有关的现金': 'other_cash_finance_in',
    '筹资活动现金流入小计': 'total_cash_finance_in',
    '偿还债务支付的现金': 'repay_debt_cash',
    '分配股利、利润或偿付利息支付的现金': 'dividend_interest_paid_cash',
    '支付其他与筹资活动有关的现金': 'other_cash_finance_out',
    '筹资活动现金流出小计': 'total_cash_finance_out',
    # 其他
    '汇率变动对现金及现金等价物的影响': 'fx_impact_on_cash',
}


def fetch_ths_finance(code: str, report_type: str, session: requests.Session) -> dict:
    """Fetch all historical data from THS for one report type"""
    _ths_limiter.acquire()
    url = f"https://basic.10jqka.com.cn/api/stock/finance/{code}_{report_type}.json"
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


def safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except:
        return None


def extract_all_data(code: str, session: requests.Session) -> dict:
    """Extract all historical data for one stock"""
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_main = pool.submit(fetch_ths_finance, code, 'main', session)
        f_debt = pool.submit(fetch_ths_finance, code, 'debt', session)
        f_benefit = pool.submit(fetch_ths_finance, code, 'benefit', session)
        f_cash = pool.submit(fetch_ths_finance, code, 'cash', session)
        
        main_data = f_main.result()
        debt_data = f_debt.result()
        benefit_data = f_benefit.result()
        cash_data = f_cash.result()
    
    return {
        'main': main_data,
        'debt': debt_data,
        'benefit': benefit_data,
        'cash': cash_data,
    }


def save_to_db_batch(all_stocks_data: list):
    """Batch save all stocks data using execute_values (much faster)"""
    if not all_stocks_data:
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Prepare main data
        main_rows = []
        for stock_code, all_data in all_stocks_data:
            if all_data['main']:
                for period, metrics in all_data['main'].items():
                    row = [stock_code, period]
                    for cn_name, en_name in MAIN_METRICS.items():
                        row.append(safe_float(metrics.get(cn_name)))
                    main_rows.append(row)
        
        if main_rows:
            cols = ['stock_code', 'report_period'] + list(MAIN_METRICS.values())
            col_names = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))
            sql = f"""
                INSERT INTO vr_ths_main ({col_names})
                VALUES %s
                ON CONFLICT (stock_code, report_period) DO UPDATE SET
                {', '.join([f"{c} = EXCLUDED.{c}" for c in cols[2:]])}
            """
            psycopg2.extras.execute_values(cur, sql, main_rows, page_size=1000)
            print(f"  Inserted {len(main_rows)} main records")
        
        # Prepare debt data
        debt_rows = []
        for stock_code, all_data in all_stocks_data:
            if all_data['debt']:
                for period, metrics in all_data['debt'].items():
                    row = [stock_code, period]
                    for cn_name, en_name in DEBT_METRICS.items():
                        row.append(safe_float(metrics.get(cn_name)))
                    debt_rows.append(row)
        
        if debt_rows:
            cols = ['stock_code', 'report_period'] + list(DEBT_METRICS.values())
            col_names = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))
            sql = f"""
                INSERT INTO vr_ths_debt ({col_names})
                VALUES %s
                ON CONFLICT (stock_code, report_period) DO UPDATE SET
                {', '.join([f"{c} = EXCLUDED.{c}" for c in cols[2:]])}
            """
            psycopg2.extras.execute_values(cur, sql, debt_rows, page_size=1000)
            print(f"  Inserted {len(debt_rows)} debt records")
        
        # Prepare benefit data
        benefit_rows = []
        for stock_code, all_data in all_stocks_data:
            if all_data['benefit']:
                for period, metrics in all_data['benefit'].items():
                    row = [stock_code, period]
                    for cn_name, en_name in BENEFIT_METRICS.items():
                        row.append(safe_float(metrics.get(cn_name)))
                    benefit_rows.append(row)
        
        if benefit_rows:
            cols = ['stock_code', 'report_period'] + list(BENEFIT_METRICS.values())
            col_names = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))
            sql = f"""
                INSERT INTO vr_ths_benefit ({col_names})
                VALUES %s
                ON CONFLICT (stock_code, report_period) DO UPDATE SET
                {', '.join([f"{c} = EXCLUDED.{c}" for c in cols[2:]])}
            """
            psycopg2.extras.execute_values(cur, sql, benefit_rows, page_size=1000)
            print(f"  Inserted {len(benefit_rows)} benefit records")
        
        # Prepare cashflow data
        cash_rows = []
        for stock_code, all_data in all_stocks_data:
            if all_data['cash']:
                for period, metrics in all_data['cash'].items():
                    row = [stock_code, period]
                    for cn_name, en_name in CASH_METRICS.items():
                        row.append(safe_float(metrics.get(cn_name)))
                    cash_rows.append(row)
        
        if cash_rows:
            cols = ['stock_code', 'report_period'] + list(CASH_METRICS.values())
            col_names = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))
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


def process_one_stock(code: str, session: requests.Session) -> tuple:
    """Process one stock: fetch data only (no save)"""
    all_data = extract_all_data(code, session)
    
    # Count records
    main_count = len(all_data['main'])
    debt_count = len(all_data['debt'])
    benefit_count = len(all_data['benefit'])
    cash_count = len(all_data['cash'])
    
    return (code, all_data), {
        'code': code,
        'main': main_count,
        'debt': debt_count,
        'benefit': benefit_count,
        'cash': cash_count,
    }


def main():
    start_time = time.monotonic()
    print(f"[{datetime.now()}] Starting THS Full History Data Extraction...")
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
    print(f"Total stocks to process: {total}")
    sys.stdout.flush()
    
    # Check already processed
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT stock_code FROM vr_ths_main")
        already_done = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        
        pending_codes = [c for c in codes if c not in already_done]
        print(f"Already processed: {len(already_done)}, Remaining: {len(pending_codes)}")
    except Exception as e:
        print(f"Failed to check existing data: {e}")
        pending_codes = codes
    
    if not pending_codes:
        print("All stocks already processed!")
        return
    
    sys.stdout.flush()
    
    # Processing
    processed_count = 0
    success_count = 0
    error_count = 0
    count_lock = threading.Lock()
    
    batch_results = []
    batch_lock = threading.Lock()
    SAVE_EVERY = 100  # batch save every 100 stocks
    
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
            save_to_db_batch(to_save)
    
    def on_stock_done(future, code):
        nonlocal processed_count, success_count, error_count
        
        with count_lock:
            processed_count += 1
        
        try:
            data_tuple, stats = future.result()
            if stats and (stats['main'] > 0 or stats['debt'] > 0 or stats['benefit'] > 0 or stats['cash'] > 0):
                with batch_lock:
                    batch_results.append(data_tuple)
                with count_lock:
                    success_count += 1
                    cur_success = success_count
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
            fut = executor.submit(process_one_stock, code, session)
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
