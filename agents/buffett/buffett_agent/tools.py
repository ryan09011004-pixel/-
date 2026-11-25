"""에이전트가 호출하는 도구: 인용 검색, 알려진 사실, 버핏 스타일 점검표.

도구는 같은 프로세스 안에서 도는 SDK MCP 서버로 묶는다(`build_server`).
"""
from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import checklist as cl
from . import quotes as qs

SERVER_NAME = "buffett"
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{n}" for n in ("search_quotes", "get_known_facts", "get_buffett_checklist")]


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


def known_facts_impl() -> str:
    return (qs.PERSONA_DIR / "facts.md").read_text(encoding="utf-8")


def checklist_impl(ticker: str) -> dict[str, Any]:
    import yfinance as yf  # 느린 임포트라 도구가 불릴 때만 읽는다

    t = yf.Ticker(ticker)
    info = t.get_info() or {}
    try:
        stmt = t.income_stmt
        income = [None if v != v else float(v) for v in stmt.loc["Net Income"].tolist()] if "Net Income" in stmt.index else []
    except Exception:
        income = []
    metrics = cl.metrics_from_yfinance(info, income)
    rows = cl.evaluate(metrics, cl.load_criteria())
    return {
        "ticker": ticker,
        "name": info.get("shortName"),
        "sector": info.get("sector"),
        "summary": cl.summarize(rows),
        "rows": rows,
        "note": "기준값은 버핏이 정한 숫자가 아니라 이 프로젝트의 임의 기본값입니다. 해자·경영진·사업 이해 가능성은 숫자로 판정하지 않습니다.",
    }


@tool("search_quotes", "버핏 주주서한에서 검증된 인용을 주제 또는 키워드로 찾는다. 인용을 쓸 때는 반드시 이 도구 결과의 ID를 붙인다.", {"query": str})
async def search_quotes(args: dict[str, Any]) -> dict[str, Any]:
    return _text(search_quotes_impl(args["query"]))


@tool("get_known_facts", "버핏과 버크셔에 대해 확인된 사실과 출처 유형, 아직 수집하지 못한 자료를 돌려준다.", {})
async def get_known_facts(args: dict[str, Any]) -> dict[str, Any]:
    return _text(known_facts_impl())


@tool("get_buffett_checklist", "티커의 재무 지표를 버핏 스타일 점검표에 대어 통과·미달·확인 불가로 표시한다(Yahoo Finance 기준).", {"ticker": str})
async def get_buffett_checklist(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(checklist_impl(args["ticker"].strip()))
    except Exception as e:  # 네트워크·티커 오류를 모델에 알려 지어내지 않게 한다
        return _text(f"점검표를 만들지 못했습니다: {e}. 수치를 추측하지 마세요.", is_error=True)


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0", tools=[search_quotes, get_known_facts, get_buffett_checklist])
