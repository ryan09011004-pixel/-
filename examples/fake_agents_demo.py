"""가짜 데이터 + 가짜 LLM으로 AI 투자자 에이전트 흐름을 확인하는 시험용 스크립트.

키·네트워크 없이 에이전트(buffett, graham 등)가 재무 스냅샷을 읽고 신호를 내서
주문으로 이어지는 흐름을 끝까지 돌린다. 모델 응답은 프롬프트 해시로 만든 가짜이고,
숫자에는 의미가 없다. 진짜 모델 호출은 일어나지 않는다.

    python examples/fake_agents_demo.py examples/agents_demo.yaml
    python examples/fake_agents_demo.py examples/agents_demo.yaml --tickers AAPL,TSLA --seed 3
"""
import argparse
import hashlib
import json
import random
import tempfile
import zlib
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console

from fake_data_demo import FakeClient
from hedge_fund.backtesting.fund import backtest_fund
from hedge_fund.data.models import FinancialMetrics
from hedge_fund.fund import Fund, load_spec
from hedge_fund.llm import PromptCache
from hedge_fund.signals import ALPHA_MODEL_REGISTRY, LLMAgent


class FakeLLM:
    """프롬프트 해시로 bullish/neutral/bearish를 정하는 가짜 모델. 호출 횟수를 센다."""

    model = "fake-llm"

    def __init__(self, seed: int):
        self.seed, self.calls = seed, 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        h = int(hashlib.sha256(f"{self.seed}|{system[:40]}|{user}".encode()).hexdigest(), 16)
        signal = ["bullish", "neutral", "bearish"][h % 3]
        return json.dumps({"signal": signal, "confidence": 50 + h % 50, "reasoning": f"가짜 응답 ({signal})"})


class FakeBreakpoints:
    def size_percentile(self, market_cap, filing_date):
        return 90


class FakeFundamentals(FakeClient):
    """FakeClient에 분기별 재무 지표를 더한 가짜 데이터."""

    def get_financial_metrics(self, ticker, end_date, period="ttm", limit=10):
        rng = random.Random(zlib.crc32(ticker.encode()) + self.seed)
        rows, day = [], date(2024, 3, 31)
        while day < date(2026, 10, 1):
            filing = day + timedelta(days=30)
            if filing.isoformat() <= end_date:
                rows.append(FinancialMetrics(
                    ticker=ticker, report_period=day.isoformat(), period="ttm", filing_date=filing.isoformat(),
                    market_cap=1e11 * rng.uniform(0.5, 2), price_to_earnings_ratio=rng.uniform(8, 40),
                    return_on_equity=rng.uniform(0.05, 0.3), gross_margin=rng.uniform(0.3, 0.6),
                    operating_margin=rng.uniform(0.1, 0.3), net_margin=rng.uniform(0.05, 0.25),
                    debt_to_equity=rng.uniform(0.1, 1.5), current_ratio=rng.uniform(0.8, 2.5),
                    revenue_growth=rng.uniform(-0.05, 0.25), earnings_per_share=rng.uniform(1, 10),
                    book_value_per_share=rng.uniform(10, 60), free_cash_flow_per_share=rng.uniform(1, 9)))
            day = (day.replace(day=1) + timedelta(days=95)).replace(day=1) - timedelta(days=1)
        return sorted(rows, key=lambda r: r.report_period, reverse=True)[:limit]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mandate")
    p.add_argument("--tickers", default="AAPL,NVDA,MSFT")
    p.add_argument("--start", default="2026-01-05")
    p.add_argument("--end", default="2026-11-13")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    spec, llm = load_spec(a.mandate), FakeLLM(a.seed)
    cache = PromptCache(Path(tempfile.mkdtemp(prefix="fake-llm-cache-")))  # 실제 캐시 폴더를 건드리지 않는다
    models = {}
    for strategy in spec.strategies:
        staff = []
        for m in strategy.models:
            cls = ALPHA_MODEL_REGISTRY[m.name]
            staff.append(cls(llm=llm, cache=cache, blind=True, breakpoints=FakeBreakpoints())
                         if issubclass(cls, LLMAgent) else cls(**m.params))
        models[strategy.name] = staff

    res = backtest_fund(Fund(spec, models=models, blind=True), a.start, a.end,
                        FakeFundamentals(a.seed), a.tickers.split(","))
    m = res.metrics
    Console().print(
        f"{res.fund} {res.start} → {res.end} · 세션 {len(res.dates)} · 리밸런싱 {m.n_cycles} · 주문 {m.n_orders} · "
        f"수익률 {m.total_return_pct:+.1%} (벤치마크 {res.benchmark} {m.benchmark_return_pct:+.1%}) · "
        f"샤프 {m.sharpe_ratio:.2f} · 최대낙폭 {m.max_drawdown_pct:.1%} · 최종 NAV {res.nav[-1]:,.0f} · "
        f"가짜 모델 호출 {llm.calls}회"
    )


if __name__ == "__main__":
    main()
