"""에이전트가 호출하는 도구: 인용 검색, 비슷한 사례, 알려진 사실, 린치 점검표.

도구는 같은 프로세스 안에서 도는 SDK MCP 서버로 묶는다(`build_server`).
"""
from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import cases as cs
from . import checklist as cl
from . import quotes as qs

SERVER_NAME = "lynch"
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{n}" for n in ("search_quotes", "find_similar_cases", "get_known_facts", "get_lynch_checklist")]


def _text(payload: Any, is_error: bool = False) -> dict[str, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    out: dict[str, Any] = {"content": [{"type": "text", "text": body}]}
    if is_error:
        out["is_error"] = True
    return out


def search_quotes_impl(query: str, limit: int = 6) -> str:
    quotes = qs.load_quotes()
    found = qs.search(quotes, query, limit)
    if not found:
        return f"'{query}'에 맞는 검증된 인용이 없습니다. 가능한 주제: {', '.join(qs.themes(quotes))}. 인용 없이 '원칙 적용 추정'으로 답하세요."
    return "\n\n".join(q.render() for q in found)


def find_similar_cases_impl(query: str, limit: int = 3) -> str:
    found = cs.search(cs.load_cases(), query, limit)
    if not found:
        return f"'{query}'와 비슷한 실제 결정 사례가 없습니다. 사례 없이 '원칙 적용 추정'으로만 답하고, 사례가 있는 것처럼 말하지 마세요."
    return "\n\n".join(c.render() for c in found)


def known_facts_impl() -> str:
    return (qs.PERSONA_DIR / "facts.md").read_text(encoding="utf-8")


def _row(df, key, col):
    try:
        v = df.loc[key, col]
        return None if v != v else float(v)
    except Exception:
        return None


def checklist_impl(ticker: str) -> dict[str, Any]:
    import yfinance as yf  # 느린 임포트라 도구가 불릴 때만 읽는다

    t = yf.Ticker(ticker)
    info = t.get_info() or {}
    inc, bs = t.income_stmt, t.balance_sheet
    cols = sorted(inc.columns, reverse=True) if inc is not None and len(inc.columns) else []
    bcols = sorted(bs.columns, reverse=True) if bs is not None and len(bs.columns) else []
    eps = [_row(inc, "Diluted EPS", c) for c in cols]
    revenue = [_row(inc, "Total Revenue", c) for c in cols]
    inventory = [_row(bs, "Inventory", c) for c in bcols]
    b0 = bcols[0] if bcols else None
    balance = {
        "total_debt": _row(bs, "Total Debt", b0),
        "equity": _row(bs, "Stockholders Equity", b0),
        "cash": _row(bs, "Cash Cash Equivalents And Short Term Investments", b0),
    }
    metrics = cl.metrics_from_yfinance(info, eps, revenue, inventory, balance)
    rows = cl.evaluate(metrics, cl.load_criteria())
    growth = metrics["eps_growth_pct"]
    return {
        "ticker": ticker,
        "name": info.get("shortName"),
        "sector": info.get("sector"),
        "category": cl.classify(info.get("sector"), eps, growth, info.get("priceToBook")),
        "reference": cl.reference(info.get("currentPrice") or info.get("regularMarketPrice"), info.get("trailingEps"), growth),
        "summary": cl.summarize(rows),
        "rows": rows,
        "note": "기준값과 분류는 린치의 책과 2차 자료를 따르려는 프로젝트 기본값이며 원서로 확인되지 않았습니다. 무료 데이터가 약 4년치뿐이라 성장률은 가능한 연수로 계산했습니다.",
    }


@tool("search_quotes", "린치의 말(1996 PBS 인터뷰 원문에서 확인한 것)을 주제 또는 키워드로 찾는다. 인용을 쓸 때는 반드시 이 도구 결과의 ID를 붙인다.", {"query": str})
async def search_quotes(args: dict[str, Any]) -> dict[str, Any]:
    return _text(search_quotes_impl(args["query"]))


@tool("find_similar_cases", "린치의 실제 투자 사례 중 질문과 비슷한 것을 찾는다. 사례를 쓸 때는 [K04]처럼 ID를 붙인다.", {"query": str})
async def find_similar_cases(args: dict[str, Any]) -> dict[str, Any]:
    return _text(find_similar_cases_impl(args["query"]))


@tool("get_known_facts", "린치에 대해 확인된 사실과 출처 유형, 아직 수집하지 못한 자료를 돌려준다.", {})
async def get_known_facts(args: dict[str, Any]) -> dict[str, Any]:
    return _text(known_facts_impl())


@tool("get_lynch_checklist", "티커의 재무 지표를 린치 스타일 점검표에 대어 통과·미달·확인 불가로 표시하고 종목 종류를 추정하며 PEG 1이 되는 가격을 계산한다(Yahoo Finance 기준).", {"ticker": str})
async def get_lynch_checklist(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(checklist_impl(args["ticker"].strip()))
    except Exception as e:  # 네트워크·티커 오류를 모델에 알려 지어내지 않게 한다
        return _text(f"점검표를 만들지 못했습니다: {e}. 수치를 추측하지 마세요.", is_error=True)


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0", tools=[search_quotes, find_similar_cases, get_known_facts, get_lynch_checklist])
