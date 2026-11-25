from buffett_agent import checklist as cl
from buffett_agent.agent import system_prompt
from buffett_agent.tools import TOOL_NAMES, known_facts_impl, search_quotes_impl


def test_metrics_units_are_normalized():
    info = {"returnOnEquity": 0.2, "debtToEquity": 50.0, "operatingMargins": 0.3, "freeCashflow": 10, "trailingPE": 18.0}
    m = cl.metrics_from_yfinance(info, [5.0, 4.0, 6.0, 7.0])
    assert m["roe_pct"] == 20.0 and m["operating_margin_pct"] == 30.0
    assert m["debt_to_equity_pct"] == 50.0 and m["profit_years_positive_ratio"] == 1.0


def test_evaluate_pass_fail_and_unknown():
    rows = cl.evaluate(
        {"roe_pct": 20.0, "debt_to_equity_pct": 300.0, "operating_margin_pct": None,
         "profit_years_positive_ratio": 0.75, "free_cashflow": 1.0, "pe_ratio": 40.0},
        cl.load_criteria(),
    )
    by = {r["id"]: r["result"] for r in rows}
    assert by == {"roe": "통과", "debt": "미달", "op_margin": "확인 불가",
                  "earnings_consistency": "미달", "fcf": "통과", "price": "미달"}
    assert cl.summarize(rows) == {"통과": 2, "미달": 3, "확인 불가": 1}


def test_system_prompt_has_guardrails():
    p = system_prompt()
    for must in ("AI 페르소나", "search_quotes", "지어내지", "투자 조언이 아닙니다", "시장 예측"):
        assert must in p


def test_tools_wiring():
    assert TOOL_NAMES == ["mcp__buffett__search_quotes", "mcp__buffett__get_known_facts", "mcp__buffett__get_buffett_checklist"]
    assert "[Q" in search_quotes_impl("moat")
    assert "인용 없이" in search_quotes_impl("비트코인 폭등")
    assert "Greg Abel" in known_facts_impl() and "2025" in known_facts_impl()
