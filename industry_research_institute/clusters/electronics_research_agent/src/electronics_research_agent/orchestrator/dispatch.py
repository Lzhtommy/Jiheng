from __future__ import annotations

from collections import defaultdict

from ..taxonomy.universe import UniverseStock, load_universe


def group_universe_by_l3(stocks: list[UniverseStock] | None = None) -> dict[str, list[UniverseStock]]:
    grouped: dict[str, list[UniverseStock]] = defaultdict(list)
    for stock in stocks or load_universe():
        grouped[stock.l3_code].append(stock)
    return dict(grouped)


def group_universe_by_l2(stocks: list[UniverseStock] | None = None) -> dict[str, list[UniverseStock]]:
    grouped: dict[str, list[UniverseStock]] = defaultdict(list)
    for stock in stocks or load_universe():
        grouped[stock.l2_code].append(stock)
    return dict(grouped)
