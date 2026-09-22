# -*- coding: utf-8 -*-
"""Fetch Shenwan 2021 L3 index constituents via akshare → swsresearch.com.

Upstream:
  akshare.index_component_sw(symbol=<index_code without .SI>)
  https://www.swsresearch.com/institute-sw/api/index_publish/details/component_stocks/

Reads L3 codes from registries/l3.yaml and writes snapshot CSVs under snapshots/.

Usage (repo root):
  pip install akshare pandas pyyaml
  python industry_data/sw2021/scripts/fetch_l3_members.py
  python industry_data/sw2021/scripts/fetch_l3_members.py --write-by-l3
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_L3 = ROOT / "registries" / "l3.yaml"
DEFAULT_OUT = ROOT / "snapshots"


def load_yaml_industries(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("industries") or [])


def fetch_one(index_code: str, retries: int = 3, sleep_s: float = 0.35) -> pd.DataFrame:
    try:
        import akshare as ak
    except ImportError as e:  # pragma: no cover
        raise SystemExit("Please install akshare: pip install akshare") from e

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            df = ak.index_component_sw(symbol=str(index_code))
            if df is None or df.empty:
                return pd.DataFrame()
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(sleep_s * (attempt + 1) * 2)
    raise RuntimeError(f"fetch failed for {index_code}: {last_err}")


def normalize_members(raw: pd.DataFrame, l3_index_si: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(
            columns=["股票代码", "股票简称", "纳入时间", "申万3级", "l3_index_code"]
        )
    df = raw.copy()
    colmap = {}
    for c in df.columns:
        s = str(c)
        if s in {"股票代码", "证券代码", "code", "symbol"} or (
            "代码" in s and "指数" not in s
        ):
            colmap[c] = "股票代码"
        elif s in {"股票简称", "证券简称", "name", "股票名称"} or "简称" in s or s == "名称":
            colmap.setdefault(c, "股票简称")
        elif "纳入" in s or s in {"in_date", "start_date"}:
            colmap[c] = "纳入时间"
    df = df.rename(columns=colmap)
    if "股票代码" not in df.columns:
        df = df.rename(columns={df.columns[0]: "股票代码"})
    out = pd.DataFrame()
    out["股票代码"] = df["股票代码"].astype(str).str.strip()
    out["股票简称"] = (
        df["股票简称"].astype(str).str.strip() if "股票简称" in df.columns else ""
    )
    out["纳入时间"] = (
        df["纳入时间"].astype(str).str.strip() if "纳入时间" in df.columns else ""
    )
    out["申万3级"] = ""
    out["l3_index_code"] = l3_index_si
    out = out[out["股票代码"].astype(bool) & (out["股票代码"] != "nan")]
    return out.reset_index(drop=True)


def enrich(members: pd.DataFrame, l3_rows: list[dict]) -> pd.DataFrame:
    by_idx = {f"{r['index_code']}.SI": r for r in l3_rows}
    rows = []
    for _, r in members.iterrows():
        meta = by_idx.get(str(r["l3_index_code"]), {})
        code = str(r["股票代码"])
        rows.append(
            {
                "l3_index_code": r["l3_index_code"],
                "l3_industry_code": meta.get("code", ""),
                "l3_name": meta.get("name", r.get("申万3级", "")),
                "l2_code": meta.get("l2_code", ""),
                "l2_name": meta.get("l2_name", ""),
                "l1_code": meta.get("l1_code", ""),
                "l1_name": meta.get("l1_name", ""),
                "股票代码": code,
                "ts_code": code,
                "股票简称": r.get("股票简称", ""),
                "纳入时间": r.get("纳入时间", ""),
                "申万3级": meta.get("name", r.get("申万3级", "")),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--l3-yaml", type=Path, default=DEFAULT_L3)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sleep", type=float, default=0.35)
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N L3 codes")
    ap.add_argument("--write-by-l3", action="store_true", help="also write per-L3 CSVs")
    args = ap.parse_args()

    l3_rows = load_yaml_industries(args.l3_yaml)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    by_dir = out_dir / "by_l3"
    if args.write_by_l3:
        by_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    failures: list[dict] = []
    codes = [r["index_code"] for r in l3_rows]
    if args.limit:
        codes = codes[: args.limit]

    for i, code in enumerate(codes):
        si = f"{code}.SI"
        try:
            raw = fetch_one(code, sleep_s=args.sleep)
            part = normalize_members(raw, si)
            if part.empty:
                # still record empty industry for transparency when write-by-l3
                if args.write_by_l3:
                    part.to_csv(by_dir / f"{si}.csv", index=False, encoding="utf-8-sig")
            else:
                if args.write_by_l3:
                    part.to_csv(by_dir / f"{si}.csv", index=False, encoding="utf-8-sig")
                frames.append(part)
            print(f"OK {i + 1}/{len(codes)} {si} rows={len(part)}", flush=True)
        except Exception as e:  # noqa: BLE001
            failures.append({"code": si, "err": str(e)})
            print(f"FAIL {si}: {e}", flush=True)
        time.sleep(args.sleep)

    members = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    enriched = enrich(members, l3_rows)

    members_path = out_dir / "sw2021_l3_stock_members.csv"
    enriched_path = out_dir / "sw2021_l3_stock_members_enriched.csv"
    lean_cols = [
        "l3_industry_code",
        "l3_index_code",
        "l3_name",
        "l2_code",
        "l2_name",
        "l1_code",
        "l1_name",
        "ts_code",
        "股票简称",
        "纳入时间",
    ]
    lean = enriched[[c for c in lean_cols if c in enriched.columns]].copy()
    lean.to_csv(members_path, index=False, encoding="utf-8-sig")
    enriched.to_csv(enriched_path, index=False, encoding="utf-8-sig")

    covered = set(enriched["l3_index_code"].unique()) if len(enriched) else set()
    official = {f"{r['index_code']}.SI" for r in l3_rows}
    summary = {
        "source": "akshare.index_component_sw → swsresearch.com component_stocks",
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "l3_attempted": len(codes),
        "l3_with_rows": len(covered),
        "stock_rows": int(len(enriched)),
        "unique_ts_codes": int(enriched["ts_code"].nunique()) if len(enriched) else 0,
        "failures": failures,
        "l3_missing_no_rows": sorted(official - covered),
        "paths": {"members": str(members_path), "enriched": str(enriched_path)},
    }
    (out_dir / "l3_members_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: summary[k] for k in summary if k != "failures"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
