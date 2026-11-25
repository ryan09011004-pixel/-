"""키·네트워크 없이 백테스트 흐름만 확인하는 시험용 스크립트.

가짜 주가와 가짜 실적 데이터로 mandate 하나를 끝까지 돌린다.
숫자에는 의미가 없고, 파이프라인이 오류 없이 도는지만 본다.
AI 호출이 필요 없는 모델(pead)만 쓸 수 있다.

    python examples/fake_data_demo.py examples/pead_demo.yaml
    python examples/fake_data_demo.py examples/pead_demo.yaml --tickers AAPL,TSLA --seed 3
"""
import argparse
import random
import zlib
from datetime import date, timedelta

from rich.console import Console

from hedge_fund.backtesting.fund import backtest_fund
from hedge_fund.data.models import EarningsData, EarningsRecord, Price
from hedge_fund.fund import Fund, load_spec

QUARTERS = [
    ("2025-06-30", "2025-07-28"), ("2025-09-30", "2025-10-28"),
    ("2025-12-31", "2026-01-28"), ("2026-03-31", "2026-04-28"),
    ("2026-06-30", "2026-07-28"), ("2026-09-30", "2026-10-28"),
]


class FakeClient:
    """DataClient 프로토콜 중 PEAD 백테스트에 필요한 부분만 구현한 가짜 데이터."""

    def __init__(self, seed: int):
        self.seed = seed
        self._cache: dict[str, list[Price]] = {}

    def _rng(self, ticker: str, salt: int = 0) -> random.Random:
        return random.Random(zlib.crc32(ticker.encode()) + self.seed * 1000 + salt)

    def get_prices(self, ticker, start_date, end_date, **kw):
        if ticker not in self._cache:
            rng, price, day, bars = self._rng(ticker), 100.0, date(2025, 6, 2), []
            while day <= date(2026, 11, 20):
                if day.weekday() < 5:
                    price *= 1 + rng.gauss(0.0004, 0.012)
                    bars.append(Price(open=price, close=price, high=price * 1.005, low=price * 0.995,
                                      volume=2_000_000, time=day.isoformat() + "T16:00:00"))
                day += timedelta(days=1)
            self._cache[ticker] = bars
        return [b for b in self._cache[ticker] if start_date <= b.time[:10] <= end_date]

    def get_earnings_history(self, ticker, limit=12):
        rng = self._rng(ticker, 1)
        records = [EarningsRecord(ticker=ticker, report_period=rp, source_type="8-K", filing_date=fd,
                                  quarterly=EarningsData(eps_surprise=rng.choice(["BEAT", "MISS"])))
                   for rp, fd in QUARTERS]
        return records[-limit:]

    def get_market_cap(self, ticker, end_date): return 1e11
    def get_snapshot(self, ticker): return None
    def get_financial_metrics(self, *a, **k): return []
    def get_news(self, *a, **k): return []
    def get_insider_trades(self, *a, **k): return []
    def get_company_facts(self, ticker): return None
    def get_earnings(self, ticker): return None
    def screen(self, *a, **k): return []
    def screener_fields(self): return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mandate", help="mandate YAML 경로")
    p.add_argument("--tickers", default="AAPL,NVDA,MSFT")
    p.add_argument("--start", default="2026-01-05")
    p.add_argument("--end", default="2026-11-13")
    p.add_argument("--seed", type=int, default=7, help="가짜 데이터 시드")
    a = p.parse_args()

    spec = load_spec(a.mandate)
    res = backtest_fund(Fund(spec, blind=True), a.start, a.end, FakeClient(a.seed), a.tickers.split(","))
    m = res.metrics
    Console().print(
        f"{res.fund} {res.start} → {res.end} · 세션 {len(res.dates)} · 리밸런싱 {m.n_cycles} · "
        f"주문 {m.n_orders} · 수익률 {m.total_return_pct:+.1%} (벤치마크 {res.benchmark} {m.benchmark_return_pct:+.1%}) · "
        f"샤프 {m.sharpe_ratio:.2f} · 최대낙폭 {m.max_drawdown_pct:.1%} · 최종 NAV {res.nav[-1]:,.0f}"
    )


if __name__ == "__main__":
    main()
