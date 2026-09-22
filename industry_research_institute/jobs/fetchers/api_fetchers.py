import re
import requests

EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/"
}

THS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://basic.10jqka.com.cn/"
}

def get_eastmoney_industry(code: str, exchange: str = "1") -> str | None:
    """
    获取东财个股所属行业 (API 1)
    :param code: 股票代码，如 "600519"
    :param exchange: 交易所代码，"1" 为沪市，"0" 为深市/北交所
    :return: 行业名称字符串，如 "白酒"
    """
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{exchange}.{code}",
        "fields": "f57,f58,f127"
    }
    
    try:
        # 加入 timeout 防止卡死
        r = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        industry = data.get("data", {}).get("f127")
        return industry
    except Exception as e:
        print(f"Error fetching Eastmoney industry for {code}: {e}")
        return None

def get_eastmoney_sectors(code: str, exchange: str = "1") -> list[dict]:
    """
    获取东财个股全部板块（行业+概念+地域） (API 2a)
    :param code: 股票代码，如 "600519"
    :param exchange: 交易所代码，"1" 为沪市，"0" 为深市/北交所
    :return: 板块列表字典，每项含 f12(板块代码), f14(板块名称), f3(涨跌幅), f128(领涨股), f140(领涨股代码), f141(类型)
    """
    url = "https://push2.eastmoney.com/api/qt/slist/get"
    params = {
        "secid": f"{exchange}.{code}",
        "spt": "3",
        "pi": "0",
        "pz": "200",
        "fields": "f12,f14,f3,f128,f140,f141"
    }
    
    try:
        r = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        data_obj = data.get("data") or {}  # 防止 data 为 None
        diff = data_obj.get("diff") or []  # 防止 diff 为 None
        # API 可能返回 dict (key 为序号) 或 list，统一转为 list
        if isinstance(diff, dict):
            diff = list(diff.values())
        return diff
    except Exception as e:
        print(f"Error fetching Eastmoney sectors for {code}: {e}")
        return []

def get_10jqka_industry(code: str) -> dict:
    """
    获取同花顺个股所属申万行业（包含一级和二级） (API 5)
    :param code: 股票代码，如 "600519"
    :return: 包含 raw, l1, l2 行业的字典
    """
    url = f"https://basic.10jqka.com.cn/{code}/company.html"
    
    try:
        r = requests.get(url, headers=THS_HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        text = r.text
        
        industry_str = None
        # 正则匹配1：申万行业直接提取
        m = re.search(r"所属申万行业[:：]\s*([^<\n]+)", text)
        if m:
            industry_str = m.group(1).strip()
        else:
            # 正则匹配2：通用 class="value" 提取
            m2 = re.search(r"所属行业.*?class=\"value\">([^<]+)</span>", text, re.DOTALL)
            if m2:
                industry_str = m2.group(1).strip()
            else:
                # 正则匹配3
                m3 = re.search(r"申万行业[:：].*?<span[^>]*>(.*?)</span>", text, re.DOTALL)
                if m3:
                    industry_str = m3.group(1).strip()
                    
        result = {"raw": industry_str, "l1": None, "l2": None}
        
        if industry_str:
            # 切分形如 "食品饮料 — 白酒" 的字符串
            parts = [p.strip() for p in re.split(r'[-—―]+', industry_str) if p.strip()]
            if len(parts) >= 1:
                result["l1"] = parts[0]
            if len(parts) >= 2:
                result["l2"] = parts[1]
                
        return result
    except Exception as e:
        print(f"Error fetching 10jqka industry for {code}: {e}")
        return {"raw": None, "l1": None, "l2": None}
