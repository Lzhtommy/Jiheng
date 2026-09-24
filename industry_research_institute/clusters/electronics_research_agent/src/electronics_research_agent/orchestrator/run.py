from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from ..agents.roles import build_org
from ..artifacts.render import write_run
from ..artifacts.schema import RunManifest
from ..config import load_settings
from ..db.queries import StockBundle, fetch_stock_bundle
from ..paths import RUNS_DIR, require_layout
from ..policy.specs import policy_for
from ..taxonomy.map_stock import map_stock
from ..taxonomy.sw import load_taxonomy
from ..taxonomy.universe import load_universe
from .aggregate import build_l1_brief, build_l2_review, build_l3_note
from .dispatch import group_universe_by_l3


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))


def cmd_map(codes: list[str]) -> int:
    require_layout()
    tax = load_taxonomy()
    rows = []
    for raw in codes:
        hit = map_stock(raw, tax)
        rows.append(
            [
                hit.stock_code,
                hit.stock_name or "—",
                f"{hit.l1_name}/{hit.l2_name}/{hit.l3_name}" if hit.found else "未匹配",
                hit.l1_code or "—",
                hit.l2_code or "—",
                hit.l3_code or "—",
                hit.source,
            ]
        )
    _print_table(rows, ["代码", "名称", "申万", "L1", "L2", "L3", "来源"])
    return 0 if all(r[-1] != "miss" for r in rows) else 1


def cmd_tree() -> int:
    require_layout()
    settings = load_settings()
    org = build_org(settings)
    uni = load_universe()
    print(f"首席 {org.chief.name} ({org.chief.code})")
    by_l3: dict[str, int] = {}
    by_l2: dict[str, int] = {}
    for s in uni:
        by_l3[s.l3_code] = by_l3.get(s.l3_code, 0) + 1
        by_l2[s.l2_code] = by_l2.get(s.l2_code, 0) + 1
    for l2 in org.supervisors.values():
        flag = "活跃" if l2.active else "stub"
        print(f"  主管 {l2.name} ({l2.code}) [{flag}] v1={by_l2.get(l2.code, 0)}")
        policy = policy_for(l2.code)
        print(f"       政策 {policy.summary_line()}")
        for code in l2.child_codes:
            l3 = org.researchers[code]
            l3_flag = "活跃" if l3.active else "stub"
            print(f"    研究员 {l3.name} ({l3.code}) [{l3_flag}] v1={by_l3.get(code, 0)}")
    return 0


def cmd_universe() -> int:
    require_layout()
    rows = []
    for s in load_universe():
        rows.append([s.stock_code, s.stock_name, s.l2_name, s.l3_name, s.class_name])
    _print_table(rows, ["代码", "名称", "L2", "L3", "class_name"])
    print(f"\ncount={len(rows)}")
    return 0


def run_research(
    as_of: str,
    out_dir: Optional[Path] = None,
    use_db: bool = True,
) -> Path:
    require_layout()
    settings = load_settings()
    org = build_org(settings)
    stocks = load_universe()
    codes = [s.stock_code for s in stocks]
    db_used = False
    bundles: dict[str, StockBundle] = {c: StockBundle(stock_code=c) for c in codes}
    if use_db:
        try:
            bundles = fetch_stock_bundle(codes, use_db=True)
            db_used = any(b.inputs or b.summary for b in bundles.values())
        except Exception as exc:
            print(f"database skipped: {exc}", file=sys.stderr)
            bundles = {c: StockBundle(stock_code=c) for c in codes}

    grouped = group_universe_by_l3(stocks)
    notes = []
    # Write every L3 role (active with stocks + stubs) so the org tree is complete.
    for l3_code, role in org.researchers.items():
        notes.append(build_l3_note(l3_code, org, grouped.get(l3_code, []), bundles))

    reviews = [build_l2_review(code, org, notes) for code in org.supervisors]
    brief = build_l1_brief(org, reviews)

    dest = Path(out_dir) if out_dir else (RUNS_DIR / as_of)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        as_of=as_of,
        version=settings.version,
        db_used=db_used,
        llm_enabled=settings.llm_enabled,
        universe_size=len(stocks),
        out_dir=str(dest),
        l3_written=[n.l3_code for n in notes],
        l2_written=[r.l2_code for r in reviews],
    )
    write_run(dest, notes, reviews, brief, manifest)
    return dest


def cmd_run(as_of: str, out_dir: Optional[str], no_db: bool) -> int:
    dest = run_research(as_of=as_of, out_dir=Path(out_dir) if out_dir else None, use_db=not no_db)
    print(f"wrote {dest}")
    print(f"  l1: {dest / 'l1' / 'brief.md'}")
    print(f"  l2: {dest / 'l2'}")
    print(f"  l3: {dest / 'l3'}")
    print(f"  manifest: {dest / 'manifest.json'}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="electronics-research-agent",
        description="Shenwan electronics L1/L2/L3 research agent cluster (self-contained).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_map = sub.add_parser("map", help="Map stock codes to Shenwan L1/L2/L3")
    p_map.add_argument("--codes", required=True, help="Comma-separated stock codes")

    sub.add_parser("tree", help="Print agent org chart")
    sub.add_parser("universe", help="List v1 universe")

    p_run = sub.add_parser("run", help="Assemble L3→L2→L1 research artifacts")
    p_run.add_argument("--as-of", default=str(date.today()), help="Run date (YYYY-MM-DD)")
    p_run.add_argument("--out-dir", default=None, help="Output directory (default runs/<as-of>)")
    p_run.add_argument("--no-db", action="store_true", help="Skip Postgres; taxonomy + universe only")

    args = parser.parse_args(argv)
    if args.cmd == "map":
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        return cmd_map(codes)
    if args.cmd == "tree":
        return cmd_tree()
    if args.cmd == "universe":
        return cmd_universe()
    if args.cmd == "run":
        return cmd_run(args.as_of, args.out_dir, args.no_db)
    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
