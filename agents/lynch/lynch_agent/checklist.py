"""린치 스타일 점검표: yfinance 값을 기준(persona/checklist.yaml)에 대어 보고 종목 종류를 대략 분류한다."""
from __future__ import annotations

import operator
from pathlib import Path
from typing import Any

import yaml

from .quotes import PERSONA_DIR

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}
GROWTH_CAP = 50.0  # 극단적 고성장은 지속되기 어려워 PEG 계산에는 50%까지만 쓴다(프로젝트 기본값)
CYCLICAL_SECTORS = {"Basic Materials", "Energy", "Industrials", "Consumer Cyclical"}


def load_criteria(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or PERSONA_DIR / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["criteria"]


def eps_growth_pct(eps_newest_first: list[float | None]) -> float | None:
    """가능한 연도 구간의 연평균 주당순이익 성장률(%). 처음과 끝이 모두 양수일 때만 계산한다."""
    vals = [e for e in eps_newest_first if e is not None]
    if len(vals) < 2 or vals[0] <= 0 or vals[-1] <= 0:
        return None
    n = len(vals) - 1
    return ((vals[0] / vals[-1]) ** (1 / n) - 1) * 100


def _growth(new: float | None, old: float | None) -> float | None:
    return None if new is None or old is None or old == 0 else (new / old - 1) * 100


def metrics_from_yfinance(
    info: dict[str, Any],
    eps: list[float | None],
    revenue: list[float | None],
    inventory: list[float | None],
    balance: dict[str, float | None],
) -> dict[str, float | None]:
    """무료 데이터에서 점검표 지표를 만든다. 값이 없으면 None(= 확인 불가)."""
    growth = eps_growth_pct(eps)
    per = info.get("trailingPE")
    used = min(growth, GROWTH_CAP) if growth is not None else None
    peg = per / used if per and per > 0 and used and used > 0 else None
    debt, equity, cash, mcap = balance.get("total_debt"), balance.get("equity"), balance.get("cash"), info.get("marketCap")
    inv_g = _growth(*inventory[:2]) if len(inventory) >= 2 else None
    rev_g = _growth(*revenue[:2]) if len(revenue) >= 2 else None
    ups = [1.0 if eps[i] is not None and eps[i + 1] is not None and eps[i] > eps[i + 1] else 0.0 for i in range(len(eps) - 1) if eps[i] is not None and eps[i + 1] is not None]
    inst = info.get("heldPercentInstitutions")
    return {
        "eps_growth_pct": growth,
        "growth_used_pct": used,
        "peg": peg,
        "debt_to_equity_pct": None if debt is None or not equity or equity <= 0 else debt / equity * 100,
        "net_cash_to_price_pct": None if cash is None or debt is None or not mcap else (cash - debt) / mcap * 100,
        "inventory_minus_sales_growth": None if inv_g is None or rev_g is None else inv_g - rev_g,
        "institutional_ownership_pct": None if inst is None else inst * 100,
        "eps_years_up_ratio": sum(ups) / len(ups) if ups else None,
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


def classify(sector: str | None, eps_newest_first: list[float | None], growth: float | None, pbr: float | None) -> dict[str, str]:
    """업종과 숫자로 린치의 6가지 종류를 대략 추정한다(책의 규칙을 그대로 옮긴 것이 아님)."""
    vals = [e for e in eps_newest_first if e is not None]
    if len(vals) >= 2 and vals[0] > 0 and vals[1] <= 0:
        return {"category": "회생주", "why": "직전 해 적자에서 흑자로 돌아섰다."}
    if pbr is not None and 0 < pbr < 1:
        return {"category": "자산주(후보)", "why": "주가가 장부상 순자산보다 낮다."}
    if growth is None:
        return {"category": "분류 불가", "why": "이익 성장률을 계산할 수 없다."}
    if growth >= 20:
        return {"category": "고성장주", "why": f"주당순이익이 연 {growth:.0f}% 늘었다."}
    if sector in CYCLICAL_SECTORS:
        return {"category": "경기순환주(후보)", "why": f"업종이 {sector}라서 경기에 따라 이익이 출렁일 수 있다."}
    if growth >= 10:
        return {"category": "우량주", "why": f"주당순이익이 연 {growth:.0f}% 늘었다."}
    return {"category": "저성장주", "why": f"주당순이익 성장률이 연 {growth:.0f}%로 낮다."}


def reference(price: float | None, eps_ttm: float | None, growth: float | None) -> dict[str, Any]:
    """목표주가가 아니라 'PEG가 1이 되는 가격 = 후행 EPS × 성장률(%)'의 역산값. 성장이 이어진다는 전제다."""
    used = None if growth is None else min(growth, GROWTH_CAP)
    out: dict[str, Any] = {"price": price, "eps_growth_pct": None if growth is None else round(growth, 1), "growth_used_pct": None if used is None else round(used, 1)}
    ok = eps_ttm is not None and eps_ttm > 0 and used is not None and used > 0
    out["price_at_peg_1"] = round(eps_ttm * used, 2) if ok else None
    out["note"] = f"목표주가가 아닙니다. 후행 주당순이익 x 이익 성장률(%, 최대 {GROWTH_CAP:.0f}%)로 PEG 1이 되는 가격을 역산한 값이며, 성장이 그대로 이어진다는 전제입니다. 기준은 프로젝트 기본값입니다."
    return out
