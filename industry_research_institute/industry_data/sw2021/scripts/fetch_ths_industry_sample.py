# -*- coding: utf-8 -*-
"""Sample-fetch Tonghuashun Shenwan L1/L2 for a stock (no L3).

Uses jobs.fetchers.api_fetchers.get_10jqka_industry — the same path as
jobs/batch_industry.py which fills vr_industry_sw.

Usage:
  python industry_data/sw2021/scripts/fetch_ths_industry_sample.py 600519
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from jobs.fetchers.api_fetchers import get_10jqka_industry  # noqa: E402


def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    result = get_10jqka_industry(code)
    print(f"code={code}")
    print(result)
    print("note: Tonghuashun company page provides L1+L2 only; no L3 field.")


if __name__ == "__main__":
    main()
