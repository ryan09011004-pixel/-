"""버핏 스타일 점검표: yfinance 값을 기준(persona/checklist.yaml)에 대어 본다."""
from __future__ import annotations

import operator
from pathlib import Path
from typing import Any

import yaml

from .quotes import PERSONA_DIR

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}


def load_criteria(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or PERSONA_DIR / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["criteria"]


def metrics_from_yfinance(info: dict[str, Any], net_income_by_year: list[float | None]) -> dict[str, float | None]:
    """yfinance의 info와 연간 순이익 목록에서 점검표 지표를 만든다. 값이 없으면 None."""

    def pct(v):  # 비율(0.2) -> %(20.0)
        return None if v is None else float(v) * 100

    years = [v for v in net_income_by_year if v is not None]
    ratio = None if not years else sum(1 for v in years if v > 0) / len(years)
    return {
        "roe_pct": pct(info.get("returnOnEquity")),
        "debt_to_equity_pct": info.get("debtToEquity"),  # yfinance는 이미 % 단위
        "operating_margin_pct": pct(info.get("operatingMargins")),
        "profit_years_positive_ratio": ratio,
        "free_cashflow": info.get("freeCashflow"),
        "pe_ratio": info.get("trailingPE"),
    }


def evaluate(metrics: dict[str, float | None], criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in criteria:
        value = metrics.get(c["metric"])
        if value is None:
            result = "확인 불가"
        else:
            result = "통과" if OPS[c["op"]](value, c["threshold"]) else "미달"
        rows.append(
            {
                "id": c["id"],
                "label": c["label"],
                "value": value,
                "rule": f'{c["op"]} {c["threshold"]}',
                "result": result,
                "quote_theme": c.get("source_theme"),
            }
        )
    return rows


def pe_reference_price(price: float | None, pe: float | None, criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """점검표의 PER 기준선에서 역산한 가격대. 목표주가가 아니라 '이 가격 이하면 PER 기준을 통과한다'는 계산이다."""
    rule = next((c for c in criteria if c["metric"] == "pe_ratio"), None)
    if not rule or not price or not pe or pe <= 0:
        return {"price": price, "note": "후행 PER이 없거나 0 이하라 계산하지 못했습니다."}
    eps = price / pe  # 후행 주당순이익(근사)
    return {
        "price": price,
        "trailing_eps": round(eps, 2),
        "pe_threshold": rule["threshold"],
        "price_at_pe_threshold": round(eps * rule["threshold"], 2),
        "note": "목표주가가 아닙니다. 후행 이익이 그대로일 때 PER 기준선(프로젝트 기본값)을 통과하는 가격입니다.",
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"통과": 0, "미달": 0, "확인 불가": 0}
    for r in rows:
        out[r["result"]] += 1
    return out
