from __future__ import annotations

from dataclasses import dataclass

from .models import Evidence


@dataclass(frozen=True)
class StockRecord:
    code: str
    name: str
    industry: str
    price: float
    change_1d: float
    market_cap_billion: float
    pe_ttm: float
    pb: float
    roe: float
    revenue_growth: float
    profit_growth: float
    dividend_yield: float
    cashflow_positive_3y: bool
    updated_at: str = "演示数据"

    def evidence(self) -> list[Evidence]:
        prefix = f"demo:{self.code}"
        return [
            Evidence(
                id=f"{prefix}:market",
                label="行情与估值快照",
                source_type="演示数据",
                locator=f"{prefix}/market",
                excerpt=f"{self.name}（{self.code}）价格 {self.price:.2f}，PE(TTM) {self.pe_ttm:.1f}，PB {self.pb:.1f}。",
            ),
            Evidence(
                id=f"{prefix}:financial",
                label="财务指标快照",
                source_type="演示数据",
                locator=f"{prefix}/financial",
                excerpt=f"ROE {self.roe:.1f}%，营收增速 {self.revenue_growth:.1f}%，净利润增速 {self.profit_growth:.1f}%。",
            ),
            Evidence(
                id=f"{prefix}:cashflow",
                label="现金流状态",
                source_type="演示数据",
                locator=f"{prefix}/cashflow",
                excerpt="近三年经营现金流均为正。" if self.cashflow_positive_3y else "近三年经营现金流并非持续为正。",
            ),
        ]


# MVP 阶段使用可重复的演示数据，所有界面均会显示“非实时”提示。
# 下一步可将此列表替换为 AKShare/Tushare/BaoStock 适配器，保持上层接口不变。
DEMO_UNIVERSE: tuple[StockRecord, ...] = (
    StockRecord("300750", "宁德时代", "新能源电池", 212.30, 1.24, 9320, 22.6, 4.1, 18.8, 11.2, 31.5, 1.1, True),
    StockRecord("002594", "比亚迪", "新能源汽车", 278.80, -0.36, 8100, 24.8, 4.5, 17.1, 18.7, 34.5, 1.2, True),
    StockRecord("600519", "贵州茅台", "白酒消费", 1428.00, 0.18, 17950, 27.9, 8.2, 34.6, 15.2, 14.3, 2.6, True),
    StockRecord("688981", "中芯国际", "半导体", 88.40, 2.05, 7010, 48.0, 2.7, 6.1, 32.1, 22.0, 0.3, False),
    StockRecord("600036", "招商银行", "银行", 39.80, -0.12, 10020, 6.5, 0.7, 11.2, 2.2, 1.8, 5.4, True),
    StockRecord("000333", "美的集团", "家电制造", 75.50, 0.76, 5280, 12.8, 2.4, 19.5, 10.5, 14.8, 3.6, True),
    StockRecord("002475", "立讯精密", "电子制造", 38.60, 1.62, 2740, 23.1, 3.2, 15.2, 12.4, 18.2, 1.6, True),
)


def get_stock(code: str) -> StockRecord | None:
    return next((item for item in DEMO_UNIVERSE if item.code == code), None)

