"""무료 연습용: 가격만 쓰는 직접 만든 모델(momentum, trend)로 백테스트를 돌린다.

데이터 공급원 두 가지 중 고른다.
  --source fake    가짜 주가 (키·네트워크 불필요)
  --source yahoo   야후 파이낸스 실제 주가 (무료, `pip install yfinance` 필요, 인터넷 필요)

    python examples/practice_demo.py examples/practice.yaml --source fake
    python examples/practice_demo.py examples/practice.yaml --source yahoo --tickers AAPL,MSFT --benchmark SPY

국내 종목은 야후 티커로 `005930.KS`(삼성전자)처럼 쓴다. 이 경우 mandate의 benchmark도 `^KS11` 등으로 바꿔야 한다.
앱 원본 코드는 수정하지 않고, 실행할 때만 모델을 등록한다. 연습용이며 투자 조언이 아니다.
"""
import argparse
from datetime import date, timedelta

import numpy as np
from rich.console import Console

from fake_data_demo import FakeClient
from hedge_fund.backtesting.fund import backtest_fund
from hedge_fund.data.models import Price
from hedge_fund.fund import Fund, load_spec
from hedge_fund.models import Signal
from hedge_fund.signals import ALPHA_MODEL_REGISTRY, QuantModel


def _closes(data_client, ticker: str, as_of: str, calendar_days: int) -> np.ndarray:
    """as_of 당일까지의 종가만 가져온다(미래 데이터 금지)."""
    start = (date.fromisoformat(as_of[:10]) - timedelta(days=calendar_days)).isoformat()
    bars = [b for b in data_client.get_prices(ticker, start, as_of[:10]) if b.time[:10] <= as_of[:10]]
    return np.array([b.close for b in bars], dtype=float)


class MomentumModel(QuantModel):
    """최근 N거래일 수익률이 높으면 매수, 낮으면 매도 쪽 의견."""

    investment_approach = "long_short"
    horizon_days = 21

    def __init__(self, lookback: int = 60) -> None:
        self.lookback = lookback

    @property
    def name(self) -> str:
        return "momentum"

    def predict(self, ticker: str, date: str, data_client) -> Signal:
        closes = _closes(data_client, ticker, date, int(self.lookback * 1.7) + 10)
        if len(closes) <= self.lookback:
            return Signal(model_name=self.name, ticker=ticker, date=date, value=0.0,
                          reasoning="데이터 부족", metadata={"abstained": True})
        ret = closes[-1] / closes[-1 - self.lookback] - 1
        return Signal(model_name=self.name, ticker=ticker, date=date, value=self._sigmoid(ret, scale=5.0),
                      reasoning=f"최근 {self.lookback}거래일 수익률 {ret:+.1%}", components={"return": float(ret)})


class TrendModel(QuantModel):
    """단기 이동평균이 장기 이동평균 위에 있으면 매수(1), 아니면 중립(0)."""

    investment_approach = "long_only"
    horizon_days = 21

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        self.fast, self.slow = fast, slow

    @property
    def name(self) -> str:
        return "trend"

    def predict(self, ticker: str, date: str, data_client) -> Signal:
        closes = _closes(data_client, ticker, date, int(self.slow * 1.7) + 10)
        if len(closes) < self.slow:
            return Signal(model_name=self.name, ticker=ticker, date=date, value=0.0,
                          reasoning="데이터 부족", metadata={"abstained": True})
        fast, slow = closes[-self.fast:].mean(), closes[-self.slow:].mean()
        return Signal(model_name=self.name, ticker=ticker, date=date, value=1.0 if fast > slow else 0.0,
                      reasoning=f"{self.fast}일선 {fast:.2f} {'>' if fast > slow else '≤'} {self.slow}일선 {slow:.2f}")


class YahooClient:
    """야후 파이낸스 가격만 제공하는 데이터 클라이언트. 나머지 데이터는 비어 있다."""

    def __init__(self) -> None:
        try:
            import yfinance
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("yfinance가 필요합니다: pip install yfinance") from exc
        self._yf, self._cache = yfinance, {}

    def get_prices(self, ticker, start_date, end_date, **kw):
        if ticker not in self._cache:
            try:
                df = self._yf.Ticker(ticker).history(start="2024-01-01", auto_adjust=True)
            except Exception as exc:
                raise SystemExit(f"{ticker}: 야후 접속 실패({type(exc).__name__}). 인터넷 연결을 확인하세요.") from exc
            if df.empty:
                raise SystemExit(f"{ticker}: 야후에서 가격을 못 가져왔습니다(티커나 네트워크 확인).")
            self._cache[ticker] = [
                Price(open=float(r.Open), close=float(r.Close), high=float(r.High), low=float(r.Low),
                      volume=int(r.Volume), time=idx.strftime("%Y-%m-%d") + "T16:00:00")
                for idx, r in df.iterrows()]
        return [b for b in self._cache[ticker] if start_date <= b.time[:10] <= end_date]

    def get_market_cap(self, ticker, end_date): return None
    def get_snapshot(self, ticker): return None
    def get_financial_metrics(self, *a, **k): return []
    def get_news(self, *a, **k): return []
    def get_insider_trades(self, *a, **k): return []
    def get_company_facts(self, ticker): return None
    def get_earnings(self, ticker): return None
    def get_earnings_history(self, *a, **k): return []
    def screen(self, *a, **k): return []
    def screener_fields(self): return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mandate")
    p.add_argument("--source", choices=["fake", "yahoo"], default="fake")
    p.add_argument("--tickers", default="AAPL,NVDA,MSFT")
    p.add_argument("--start", default="2026-01-05")
    p.add_argument("--end", default="2026-11-13")
    p.add_argument("--seed", type=int, default=7, help="가짜 데이터 시드(fake일 때만)")
    a = p.parse_args()

    ALPHA_MODEL_REGISTRY["momentum"] = MomentumModel   # load_spec이 이름을 검증하기 전에 등록
    ALPHA_MODEL_REGISTRY["trend"] = TrendModel
    spec = load_spec(a.mandate)
    client = YahooClient() if a.source == "yahoo" else FakeClient(a.seed)
    res = backtest_fund(Fund(spec, blind=True), a.start, a.end, client, a.tickers.split(","))
    m = res.metrics
    Console().print(
        f"{res.fund} [{a.source}] {res.start} → {res.end} · 세션 {len(res.dates)} · 리밸런싱 {m.n_cycles} · 주문 {m.n_orders} · "
        f"수익률 {m.total_return_pct:+.1%} (벤치마크 {res.benchmark} {m.benchmark_return_pct:+.1%}) · "
        f"샤프 {m.sharpe_ratio:.2f} · 최대낙폭 {m.max_drawdown_pct:.1%} · 최종 NAV {res.nav[-1]:,.0f}"
    )


if __name__ == "__main__":
    main()
