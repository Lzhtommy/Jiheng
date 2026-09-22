# -*- coding: utf-8 -*-
"""Compare THS DB L1/L2 against industry_data/sw2021 baseline registries."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
L2_PATH = ROOT / "registries" / "l2.yaml"
L1_PATH = ROOT / "registries" / "l1.yaml"

DB = {
    "host": os.environ.get("VR_PG_HOST", "193.112.152.137"),
    "port": int(os.environ.get("VR_PG_PORT", "5432")),
    "user": os.environ.get("VR_PG_USER", "postgres"),
    "password": os.environ.get("VR_PG_PASSWORD", ""),
    "database": os.environ.get("VR_PG_DATABASE", "thronepath_pg"),
}


def main() -> int:
    l1 = yaml.safe_load(L1_PATH.read_text(encoding="utf-8"))["industries"]
    l2 = yaml.safe_load(L2_PATH.read_text(encoding="utf-8"))["industries"]
    l2_names = {r["name"] for r in l2}
    l2_alias = set()
    for r in l2:
        l2_alias.update(r.get("aliases") or [])
    l1_names = {r["name"] for r in l1}

    conn = psycopg2.connect(**DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT industry_l1, industry_l2, COUNT(*) AS cnt
        FROM vr_industry_sw
        WHERE industry_l2 IS NOT NULL AND TRIM(industry_l2) <> ''
        GROUP BY industry_l1, industry_l2
        """
    )
    ths = cur.fetchall()
    conn.close()

    exact = alias = miss = 0
    miss_rows = []
    for r in ths:
        name = r["industry_l2"]
        if name in l2_names:
            exact += 1
        elif name in l2_alias:
            alias += 1
        else:
            miss += 1
            miss_rows.append(r)

    l1_miss = sorted({r["industry_l1"] for r in ths} - l1_names)
    ths_l2 = {r["industry_l2"] for r in ths}
    official_unused = sorted(l2_names - ths_l2)

    print(f"baseline L1={len(l1)} L2={len(l2)}")
    print(f"THS distinct pairs={len(ths)}")
    print(f"L2 exact={exact} alias={alias} miss={miss}")
    print(f"L1 miss={l1_miss}")
    print(f"official L2 absent in THS ({len(official_unused)}): {official_unused}")
    if miss_rows:
        print("THS L2 not in baseline:")
        for r in sorted(miss_rows, key=lambda x: -x["cnt"])[:20]:
            print(f"  {r['cnt']} {r['industry_l1']}/{r['industry_l2']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
