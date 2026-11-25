"""공시된 거래를 종목별로 집계한다. 금액은 구간이라 합계도 구간(최소~최대)으로만 말한다."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .ptr import Trade

SIGN = {"P": 1, "S": -1, "S (partial)": -1, "E": 0}


def delay_days(trade: Trade, filing_date: str) -> int:
    """거래일에서 공시(제출)일까지 일수. 법정 기한은 거래를 안 날부터 45일이다."""
    return (date.fromisoformat(filing_date) - date.fromisoformat(trade.txn_date)).days


def net_by_ticker(trades: list[Trade]) -> list[dict]:
    """종목별 매수·매도 금액 구간 합계와 순매수 구간. 티커가 없는 자산은 자산명으로 묶는다."""
    acc: dict[str, dict] = defaultdict(lambda: {"buys": 0, "sells": 0, "buy_low": 0, "buy_high": 0, "sell_low": 0, "sell_high": 0, "owners": set(), "options": 0})
    for t in trades:
        key = t.ticker or t.asset
        a = acc[key]
        a["owners"].add(t.owner)
        a["options"] += 1 if t.asset_code == "OP" else 0
        lo, hi = t.amount_low or 0, t.amount_high if t.amount_high is not None else (t.amount_low or 0)
        sign = SIGN.get(t.txn_type, 0)
        if sign > 0:
            a["buys"] += 1
            a["buy_low"] += lo
            a["buy_high"] += hi
        elif sign < 0:
            a["sells"] += 1
            a["sell_low"] += lo
            a["sell_high"] += hi
    rows = []
    for key, a in acc.items():
        rows.append(
            {
                "key": key,
                "buys": a["buys"],
                "sells": a["sells"],
                "options": a["options"],
                "owners": sorted(a["owners"]),
                "buy_range": (a["buy_low"], a["buy_high"]),
                "sell_range": (a["sell_low"], a["sell_high"]),
                # 순매수 구간: 최소 = 매수 최소 - 매도 최대, 최대 = 매수 최대 - 매도 최소
                "net_range": (a["buy_low"] - a["sell_high"], a["buy_high"] - a["sell_low"]),
            }
        )
    return sorted(rows, key=lambda r: -(abs(r["net_range"][0]) + abs(r["net_range"][1])))


def summarize(trades: list[Trade]) -> dict:
    return {
        "trades": len(trades),
        "buys": sum(1 for t in trades if SIGN.get(t.txn_type) == 1),
        "sells": sum(1 for t in trades if SIGN.get(t.txn_type) == -1),
        "options": sum(1 for t in trades if t.asset_code == "OP"),
        "owners": sorted({t.owner for t in trades}),
        "tickers": len({t.ticker or t.asset for t in trades}),
    }
