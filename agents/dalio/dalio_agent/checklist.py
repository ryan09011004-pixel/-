"""달리오 스타일 점검표: 포트폴리오(또는 자산 하나)의 위험 균형과 환경 쏠림을 계산하고 기준(persona/checklist.yaml)에 대어 본다."""
from __future__ import annotations

import math
import operator
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .quotes import PERSONA_DIR

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}
INFLATION = {"GLD", "IAU", "GLDM", "SGOL", "IAUM", "SLV", "PPLT", "TIP", "SCHP", "VTIP", "STIP", "DBC", "GSG", "PDBC", "USCI", "COMT"}
BONDS = {"TLT", "IEF", "AGG", "BND", "GOVT", "VGLT", "EDV", "ZROZ", "TLH", "SPTL", "VGIT", "SCHZ", "LQD", "SHY", "SHV", "BIL"}


def load_criteria(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or PERSONA_DIR / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["criteria"]


def category(ticker: str) -> str:
    """대표 ETF 이름 기준의 단순 분류. 목록에 없으면 주식으로 본다."""
    t = ticker.upper()
    return "물가대비" if t in INFLATION else "채권" if t in BONDS else "주식"


def parse_portfolio(text: str) -> dict[str, float]:
    """'SPY:30,TLT:40' 또는 'NVDA' 또는 'SPY,TLT'(동일 비중)를 비중(합 1)으로 바꾼다."""
    items = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    if not items or len(items) > 12:
        raise ValueError("티커를 1~12개 입력하세요. 예: SPY:30,TLT:40,GLD:15,DBC:15")
    out: dict[str, float] = {}
    for it in items:
        name, _, w = it.partition(":")
        name = name.strip().upper()
        if not name or not all(c.isalnum() or c in ".-^=" for c in name):
            raise ValueError(f"티커 형식이 올바르지 않습니다: {it}")
        out[name] = out.get(name, 0.0) + (float(w) if w.strip() else 1.0)
    total = sum(out.values())
    if total <= 0 or any(v < 0 for v in out.values()):
        raise ValueError("비중은 0보다 커야 합니다(공매도는 다루지 않습니다).")
    return {k: v / total for k, v in out.items()}


def portfolio_metrics(returns: np.ndarray, tickers: list[str], weights: list[float]) -> dict[str, Any]:
    """returns: 일별 수익률 (기간 x 자산). 위험 기여도, 평균 상관, 환경별 비중, 최대 낙폭을 계산한다."""
    r = np.atleast_2d(returns)
    if r.shape[1] != len(tickers):
        r = r.reshape(-1, len(tickers))
    w = np.array(weights, dtype=float)
    cov = np.atleast_2d(np.cov(r.T, ddof=1)) * 252
    vols = np.sqrt(np.diag(cov))
    port_var = float(w @ cov @ w)
    rc = (w * (cov @ w) / port_var * 100) if port_var > 0 else np.full(len(w), math.nan)
    n = len(tickers)
    avg_corr = None
    if n > 1:
        corr = np.corrcoef(r.T)
        avg_corr = float((corr.sum() - n) / (n * (n - 1)))
    wealth = np.cumprod(1 + r @ w)
    max_dd = float((wealth / np.maximum.accumulate(wealth) - 1).min() * 100)
    cat_w = {"주식": 0.0, "채권": 0.0, "물가대비": 0.0}
    for t, x in zip(tickers, w):
        cat_w[category(t)] += float(x) * 100
    return {
        "asset_count": float(n),
        "max_risk_contribution_pct": float(np.nanmax(rc)),
        "risk_contribution_pct": {t: round(float(x), 1) for t, x in zip(tickers, rc)},
        "avg_pairwise_correlation": avg_corr,
        "inflation_hedge_weight_pct": cat_w["물가대비"],
        "bond_weight_pct": cat_w["채권"],
        "category_weights_pct": {k: round(v, 1) for k, v in cat_w.items()},
        "max_drawdown_pct": max_dd,
        "annual_vol_pct": {t: round(float(v) * 100, 1) for t, v in zip(tickers, vols)},
        "portfolio_vol_pct": round(math.sqrt(port_var) * 100, 1) if port_var > 0 else None,
    }


def inverse_vol_weights(vols_pct: dict[str, float]) -> dict[str, float]:
    """변동성 역수 비중(단순 계산 참고값). 달리오의 실제 올웨더 비중이 아니다."""
    inv = {t: 1 / v for t, v in vols_pct.items() if v and v > 0}
    s = sum(inv.values())
    return {t: round(x / s * 100, 1) for t, x in inv.items()} if s else {}


def evaluate(metrics: dict[str, Any], criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in criteria:
        value = metrics.get(c["metric"])
        if value is None or (isinstance(value, float) and math.isnan(value)):
            result, value = "확인 불가", None
        else:
            result = "통과" if OPS[c["op"]](value, c["threshold"]) else "미달"
        rows.append({"id": c["id"], "label": c["label"], "value": value, "rule": f'{c["op"]} {c["threshold"]}', "result": result})
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"통과": 0, "미달": 0, "확인 불가": 0}
    for r in rows:
        out[r["result"]] += 1
    return out


def environment_correlations(asset: np.ndarray, benchmarks: dict[str, np.ndarray]) -> dict[str, float]:
    """자산 하나가 주식(SPY)·장기채(TLT)·금(GLD)과 같이 움직이는 정도(상관계수)."""
    return {k: round(float(np.corrcoef(asset, v)[0, 1]), 2) for k, v in benchmarks.items() if len(v) == len(asset) and len(asset) > 2}
