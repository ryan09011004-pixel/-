import math

from graham_agent import checklist as cl
from graham_agent.agent import system_prompt
from graham_agent.tools import TOOL_NAMES, find_similar_cases_impl, known_facts_impl, search_quotes_impl


def test_graham_number_and_ncav():
    assert math.isclose(cl.graham_number(3.0, 30.0), math.sqrt(22.5 * 3 * 30))  # 약 45.0
    assert cl.graham_number(-1.0, 30.0) is None and cl.graham_number(3.0, None) is None  # 적자·결측이면 계산하지 않음
    assert cl.ncav_per_share(500.0, 200.0, 100.0) == 3.0 and cl.ncav_per_share(500.0, 200.0, 0) is None


def test_reference_is_derived_not_a_target():
    ref = cl.reference(60.0, 3.0, 30.0, 3.0)
    assert ref["price_at_graham_number"] == round(math.sqrt(22.5 * 90), 2) and ref["net_net_buy_price"] == 2.0
    assert ref["price_vs_graham_number_pct"] > 0 and "목표주가가 아닙니다" in ref["note"]
    assert cl.reference(60.0, -1.0, 30.0, -5.0)["price_at_graham_number"] is None


def test_metrics_and_evaluate_with_unknowns():
    info = {"financialCurrency": "USD", "totalRevenue": 9e8, "currentRatio": 2.5, "currentPrice": 20.0, "priceToBook": 1.2}
    bal = {"current_assets": 500.0, "current_liabilities": 200.0, "long_term_debt": 100.0}
    m = cl.metrics_from_yfinance(info, [5.0, 4.0, 6.0], [2.0, 2.0, 2.0], bal, [-1.0, -1.0, -1.0])
    assert m["ltdebt_to_working_capital"] == 100.0 / 300.0 and m["per_avg_earnings"] == 10.0
    assert math.isclose(m["per_x_pbr"], 12.0) and m["dividend_years_ratio"] == 1.0
    by = {r["id"]: r["result"] for r in cl.evaluate(m, cl.load_criteria())}
    assert set(by.values()) == {"통과"}
    unknown = cl.evaluate(cl.metrics_from_yfinance({}, [], [], {}, []), cl.load_criteria())
    assert {r["result"] for r in unknown} <= {"확인 불가"} | {"통과", "미달"} and cl.summarize(unknown)["확인 불가"] >= 5


def test_non_usd_revenue_is_not_compared():
    m = cl.metrics_from_yfinance({"financialCurrency": "KRW", "totalRevenue": 4e12}, [], [], {}, [])
    assert m["revenue_usd"] is None  # 통화가 다르면 달러 기준(5억)과 비교하지 않는다


def test_system_prompt_has_guardrails_and_format():
    p = system_prompt()
    for must in ("AI 페르소나", "search_quotes", "find_similar_cases", "투자 조언이 아닙니다", "정확히 3줄", "📘 **벤저민 그레이엄** · AI 재현", "목표주가 아님", "지어내지"):
        assert must in p


def test_tools_wiring():
    assert TOOL_NAMES == ["mcp__graham__search_quotes", "mcp__graham__find_similar_cases", "mcp__graham__get_known_facts", "mcp__graham__get_graham_checklist"]
    assert "[G" in search_quotes_impl("margin_of_safety")
    assert "[K01]" in find_similar_cases_impl("시장 씨 변동") and "사례가 있는 것처럼" in find_similar_cases_impl("zzzz qqqq")
    assert "1976" in known_facts_impl() and "미확인" in known_facts_impl()


def test_reference_gives_ratio_not_only_price():
    from graham_agent import checklist as cl

    r = cl.reference(100.0, 4.0, 20.0, None)  # 그레이엄 수 = √(22.5×4×20) ≈ 42.4
    assert r["graham_number_vs_price_pct"] == -57.6
