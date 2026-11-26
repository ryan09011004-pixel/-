"""에이전트가 호출하는 도구: 인용 검색, 비슷한 사례, 알려진 사실, 소로스 점검표.

도구는 같은 프로세스 안에서 도는 SDK MCP 서버로 묶는다(`build_server`).
"""
from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import cases as cs
from . import checklist as cl
from . import quotes as qs

SERVER_NAME = "soros"
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{n}" for n in ("search_quotes", "find_similar_cases", "get_known_facts", "get_soros_checklist")]


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


def _closes(ticker: str):
    import yfinance as yf  # 느린 임포트라 도구가 불릴 때만 읽는다

    px = yf.download(ticker, period="3y", auto_adjust=True, progress=False)["Close"]
    if getattr(px, "ndim", 1) == 2:
        px = px.iloc[:, 0]
    return px.dropna().to_numpy(dtype=float)


def checklist_impl(ticker: str) -> dict[str, Any]:
    t = ticker.strip().upper()
    if not t or not all(c.isalnum() or c in ".-^=" for c in t):
        raise ValueError(f"티커 형식이 올바르지 않습니다: {ticker}")
    close = _closes(t)
    if len(close) < 60:
        raise ValueError("가격 데이터가 부족합니다(티커를 확인하세요).")
    metrics = cl.metrics_from_prices(close)
    rows = cl.evaluate(metrics, cl.load_criteria())
    levels = cl.reference_levels(close)
    return {
        "ticker": t,
        "days_of_data": int(len(close)),
        "summary": cl.summarize(rows),
        "rows": rows,
        "stage_hypothesis": cl.classify_stage(metrics),
        "reference_levels": levels,
        "note": "기준값과 단계 판정은 소로스가 정한 것이 아니라 이 프로젝트의 기본값이며 가설입니다. 참고 기준선은 목표 주가가 아닙니다. 최근 3년 일별 종가(무료 Yahoo Finance) 기준이며 실적·신용 같은 기초 여건은 보지 않습니다.",
    }


@tool("search_quotes", "소로스의 글(2013년 기고문과 2009년 강연 원문에서 확인한 것)을 주제 또는 키워드로 찾는다. 인용을 쓸 때는 반드시 이 도구 결과의 ID를 붙인다.", {"query": str})
async def search_quotes(args: dict[str, Any]) -> dict[str, Any]:
    return _text(search_quotes_impl(args["query"]))


@tool("find_similar_cases", "소로스가 글에서 직접 설명한 투자 사례 중 질문과 비슷한 것을 찾는다. 사례를 쓸 때는 [K02]처럼 ID를 붙인다.", {"query": str})
async def find_similar_cases(args: dict[str, Any]) -> dict[str, Any]:
    return _text(find_similar_cases_impl(args["query"]))


@tool("get_known_facts", "소로스에 대해 확인된 사실과 출처 유형, 아직 수집하지 못한 자료를 돌려준다.", {})
async def get_known_facts(args: dict[str, Any]) -> dict[str, Any]:
    return _text(known_facts_impl())


@tool("get_soros_checklist", "티커 하나(예: NVDA)의 가격이 200일선에서 얼마나 벌어졌는지, 12개월 상승과 가속, 변동성, 낙폭, 하락 비대칭을 소로스 스타일 점검표에 대어 보고 붐-버스트 단계 가설과 참고 기준선(50·200일선)을 돌려준다(Yahoo Finance 3년 기준).", {"ticker": str})
async def get_soros_checklist(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(checklist_impl(args["ticker"]))
    except Exception as e:  # 네트워크·티커 오류를 모델에 알려 지어내지 않게 한다
        return _text(f"점검표를 만들지 못했습니다(입력 예: NVDA): {e}. 수치를 추측하지 마세요.", is_error=True)


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0", tools=[search_quotes, find_similar_cases, get_known_facts, get_soros_checklist])
