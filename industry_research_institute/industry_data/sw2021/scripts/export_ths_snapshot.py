# -*- coding: utf-8 -*-
"""Export distinct L1/L2 names from vr_industry_sw (Tonghuashun-fed table).

Requires DB env (or project defaults used by jobs):
  VR_PG_HOST VR_PG_PORT VR_PG_USER VR_PG_PASSWORD VR_PG_DATABASE

Usage:
  python industry_data/sw2021/scripts/export_ths_snapshot.py
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import psycopg2.extras
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "snapshots" / "ths_vr_industry_sw_l1_l2.yaml"
NAME_MAP = ROOT / "registries" / "name_to_code.yaml"

DB = {
    "host": os.environ.get("VR_PG_HOST", ""),
    "port": int(os.environ.get("VR_PG_PORT", "5432")),
    "user": os.environ.get("VR_PG_USER", "postgres"),
    "password": os.environ.get("VR_PG_PASSWORD", ""),
    "database": os.environ.get("VR_PG_DATABASE", ""),
}


def main() -> None:
    name_to_l2 = {}
    if NAME_MAP.exists():
        data = yaml.safe_load(NAME_MAP.read_text(encoding="utf-8")) or {}
        name_to_l2 = data.get("l2_by_name") or {}
        name_to_l1 = data.get("l1_by_name") or {}
    else:
        name_to_l1 = {}

    conn = psycopg2.connect(**DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT industry_l1, industry_l2, COUNT(*) AS cnt
        FROM vr_industry_sw
        WHERE industry_l2 IS NOT NULL AND TRIM(industry_l2) <> ''
        GROUP BY industry_l1, industry_l2
        ORDER BY industry_l1, industry_l2
        """
    )
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS n FROM vr_industry_sw")
    total = cur.fetchone()["n"]
    conn.close()

    pairs = []
    matched = 0
    for r in rows:
        l2_code = name_to_l2.get(r["industry_l2"])
        l1_code = name_to_l1.get(r["industry_l1"])
        if l2_code:
            matched += 1
        pairs.append(
            {
                "industry_l1": r["industry_l1"],
                "industry_l2": r["industry_l2"],
                "count": int(r["cnt"]),
                "sw_l1_code": l1_code,
                "sw_l2_code": l2_code,
                "matched_official_l2": bool(l2_code),
            }
        )

    payload = {
        "source": "vr_industry_sw (populated by jobs/batch_industry.py via get_10jqka_industry)",
        "baseline": "industry_data/sw2021",
        "stock_rows": total,
        "distinct_l1_l2_pairs": len(pairs),
        "matched_to_official_l2": matched,
        "match_rate": round(matched / len(pairs), 4) if pairs else 0.0,
        "pairs": pairs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "# AUTO snapshot from Tonghuashun-fed DB\n"
        + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"wrote {OUT} pairs={len(pairs)} matched={matched}/{len(pairs)}")


if __name__ == "__main__":
    main()
