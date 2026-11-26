"""에이전트가 호출하는 도구: 인용 검색, 비슷한 사례, 알려진 사실, 달리오 점검표.

도구는 같은 프로세스 안에서 도는 SDK MCP 서버로 묶는다(`build_server`).
"""
from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import cases as cs
from . import checklist as cl
from . import quotes as qs

SERVER_NAME = "dalio"
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{n}" for n in ("search_quotes", "find_similar_cases", "get_known_facts", "get_dalio_checklist")]


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


def _returns(tickers: list[str]):
    import yfinance as yf  # 느린 임포트라 도구가 불릴 때만 읽는다

    px = yf.download(tickers, period="3y", auto_adjust=True, progress=False)["Close"]
    if getattr(px, "ndim", 2) == 1:
        px = px.to_frame(tickers[0])
    return px[tickers].pct_change().dropna()


def checklist_impl(portfolio: str) -> dict[str, Any]:
    weights = cl.parse_portfolio(portfolio)
    tickers = list(weights)
    bench = [b for b in ("SPY", "TLT", "GLD") if b not in tickers] if len(tickers) == 1 else []
    ret = _returns(tickers + bench)
    if len(ret) < 60:
        raise ValueError("가격 데이터가 부족합니다(티커를 확인하세요).")
    metrics = cl.portfolio_metrics(ret[tickers].to_numpy(), tickers, [weights[t] for t in tickers])
    rows = cl.evaluate(metrics, cl.load_criteria())
    out: dict[str, Any] = {
        "portfolio": {t: round(w * 100, 1) for t, w in weights.items()},
        "days_of_data": int(len(ret)),
        "summary": cl.summarize(rows),
        "rows": rows,
        "details": {k: metrics[k] for k in ("risk_contribution_pct", "category_weights_pct", "annual_vol_pct", "portfolio_vol_pct")},
        "reference": {
            "inverse_vol_weights": cl.inverse_vol_weights(metrics["annual_vol_pct"]),
            "note": "변동성 역수로 계산한 단순 참고 비중입니다. 달리오의 실제 올웨더 비중이 아니며 추천도 아닙니다.",
        },
        "note": "기준값과 환경 분류는 달리오가 정한 것이 아니라 이 프로젝트의 기본값입니다. 최근 3년 일별 수익률(무료 Yahoo Finance) 기준이며 과거가 미래를 보장하지 않습니다.",
    }
    if len(tickers) == 1:
        a = ret[tickers[0]].to_numpy()
        out["environment_correlation"] = cl.environment_correlations(a, {b: ret[b].to_numpy() for b in ("SPY", "TLT", "GLD") if b in ret.columns} | ({tickers[0]: a} if tickers[0] in ("SPY", "TLT", "GLD") else {}))
    return out


@tool("search_quotes", "달리오의 글(서브스택 원문에서 확인한 것)을 주제 또는 키워드로 찾는다. 인용을 쓸 때는 반드시 이 도구 결과의 ID를 붙인다.", {"query": str})
async def search_quotes(args: dict[str, Any]) -> dict[str, Any]:
    return _text(search_quotes_impl(args["query"]))


@tool("find_similar_cases", "달리오가 글에서 직접 설명한 투자 사례 중 질문과 비슷한 것을 찾는다. 사례를 쓸 때는 [K02]처럼 ID를 붙인다.", {"query": str})
async def find_similar_cases(args: dict[str, Any]) -> dict[str, Any]:
    return _text(find_similar_cases_impl(args["query"]))


@tool("get_known_facts", "달리오에 대해 확인된 사실과 출처 유형, 아직 수집하지 못한 자료를 돌려준다.", {})
async def get_known_facts(args: dict[str, Any]) -> dict[str, Any]:
    return _text(known_facts_impl())


@tool("get_dalio_checklist", "티커 하나 또는 포트폴리오(예: \"SPY:30,TLT:40,GLD:15,DBC:15\")의 위험 기여도·상관·환경별 비중·최대 낙폭을 달리오 스타일 점검표에 대어 보고 변동성 역수 참고 비중을 계산한다(Yahoo Finance 3년 기준).", {"portfolio": str})
async def get_dalio_checklist(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(checklist_impl(args["portfolio"].strip()))
    except Exception as e:  # 네트워크·티커 오류를 모델에 알려 지어내지 않게 한다
        return _text(f"점검표를 만들지 못했습니다(입력 예: SPY:30,TLT:40,GLD:15,DBC:15): {e}. 수치를 추측하지 마세요.", is_error=True)


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0", tools=[search_quotes, find_similar_cases, get_known_facts, get_dalio_checklist])
