"""그레이엄 방어적 투자자 점검표: yfinance 값을 기준(persona/checklist.yaml)에 대어 보고 그레이엄 수·NCAV를 계산한다."""
from __future__ import annotations

import math
import operator
from pathlib import Path
from typing import Any

import yaml

from .quotes import PERSONA_DIR

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}
GRAHAM_K = 22.5  # PER 15 x PBR 1.5. 프로젝트 기본값(원서 확인 전)


def load_criteria(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or PERSONA_DIR / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["criteria"]


def _ratio(values: list[float | None], ok) -> float | None:
    vals = [v for v in values if v is not None]
    return None if not vals else sum(1 for v in vals if ok(v)) / len(vals)


def metrics_from_yfinance(
    info: dict[str, Any],
    net_income: list[float | None],
    eps: list[float | None],
    balance: dict[str, float | None],
    dividends_paid: list[float | None],
) -> dict[str, float | None]:
    """무료 데이터에서 점검표 지표를 만든다. 값이 없으면 None(= 확인 불가)."""
    usd = (info.get("financialCurrency") or "USD") == "USD"
    ca, cl, ltd = balance.get("current_assets"), balance.get("current_liabilities"), balance.get("long_term_debt")
    wc = None if ca is None or cl is None else ca - cl
    if ltd is None or wc is None:
        ltd_wc = None
    elif ltd == 0:
        ltd_wc = 0.0
    else:
        ltd_wc = ltd / wc if wc > 0 else float("inf")  # 운전자본이 없거나 음수면 기준 미달
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    recent = [e for e in eps[:3] if e is not None]
    avg_eps = sum(recent) / len(recent) if recent else None
    per_avg = price / avg_eps if price and avg_eps and avg_eps > 0 else None
    pbr = info.get("priceToBook")
    return {
        "revenue_usd": info.get("totalRevenue") if usd else None,
        "current_ratio": info.get("currentRatio") or (ca / cl if ca and cl else None),
        "ltdebt_to_working_capital": ltd_wc,
        "profit_years_positive_ratio": _ratio(net_income, lambda v: v > 0),
        "dividend_years_ratio": _ratio([None if d is None else abs(d) for d in dividends_paid], lambda v: v > 0),
        "per_avg_earnings": per_avg,
        "pbr": pbr,
        "per_x_pbr": per_avg * pbr if per_avg is not None and pbr is not None else None,
    }


def evaluate(metrics: dict[str, float | None], criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in criteria:
        value = metrics.get(c["metric"])
        if value is None:
            result = "확인 불가"
        else:
            result = "통과" if OPS[c["op"]](value, c["threshold"]) else "미달"
        rows.append({"id": c["id"], "label": c["label"], "value": value, "rule": f'{c["op"]} {c["threshold"]}', "result": result})
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"통과": 0, "미달": 0, "확인 불가": 0}
    for r in rows:
        out[r["result"]] += 1
    return out


def graham_number(eps: float | None, bvps: float | None) -> float | None:
    """그레이엄 수 = √(22.5 × 주당순이익 × 주당순자산). 둘 중 하나라도 0 이하면 계산하지 않는다."""
    if eps is None or bvps is None or eps <= 0 or bvps <= 0:
        return None
    return math.sqrt(GRAHAM_K * eps * bvps)


def ncav_per_share(current_assets: float | None, total_liabilities: float | None, shares: float | None) -> float | None:
    """순유동자산가치(NCAV) 주당 값 = (유동자산 - 총부채) / 주식 수."""
    if current_assets is None or total_liabilities is None or not shares or shares <= 0:
        return None
    return (current_assets - total_liabilities) / shares


def reference(price: float | None, eps: float | None, bvps: float | None, ncav_ps: float | None) -> dict[str, Any]:
    """목표주가가 아니라 '이 가격 이하면 그레이엄 수·NCAV 기준을 통과한다'는 역산값."""
    gn = graham_number(eps, bvps)
    out: dict[str, Any] = {
        "price": price,
        "price_at_graham_number": None if gn is None else round(gn, 2),
        "price_vs_graham_number_pct": None if gn is None or not price else round((price / gn - 1) * 100, 1),
        "ncav_per_share": None if ncav_ps is None else round(ncav_ps, 2),
        "net_net_buy_price": None if ncav_ps is None or ncav_ps <= 0 else round(ncav_ps * 2 / 3, 2),
    }
    out["note"] = "목표주가가 아닙니다. 후행 이익·장부가가 그대로일 때 그레이엄 수(√(22.5×EPS×BVPS))와 NCAV 2/3 기준에서 역산한 값입니다. 계수는 프로젝트 기본값입니다."
    return out
