import math

from lynch_agent import checklist as cl
from lynch_agent.agent import system_prompt
from lynch_agent.tools import TOOL_NAMES, find_similar_cases_impl, known_facts_impl, search_quotes_impl


def test_eps_growth_is_compound_and_needs_positive_ends():
    assert math.isclose(cl.eps_growth_pct([2.0, 1.5, 1.0]), ((2.0 / 1.0) ** 0.5 - 1) * 100)
    assert cl.eps_growth_pct([1.0, -0.5]) is None and cl.eps_growth_pct([1.0]) is None


def test_peg_uses_capped_growth():
    info = {"trailingPE": 20.0}
    m = cl.metrics_from_yfinance(info, [4.0, 2.0, 1.0], [], [], {})
    assert m["eps_growth_pct"] == 100.0 and m["growth_used_pct"] == cl.GROWTH_CAP and math.isclose(m["peg"], 20.0 / cl.GROWTH_CAP)


def test_inventory_net_cash_and_institutions():
    info = {"trailingPE": 10.0, "marketCap": 1000.0, "heldPercentInstitutions": 0.4}
    bal = {"total_debt": 100.0, "equity": 400.0, "cash": 300.0}
    m = cl.metrics_from_yfinance(info, [1.2, 1.0, 0.8], [110.0, 100.0], [105.0, 100.0], bal)
    assert math.isclose(m["inventory_minus_sales_growth"], -5.0) and math.isclose(m["net_cash_to_price_pct"], 20.0)
    assert m["debt_to_equity_pct"] == 25.0 and math.isclose(m["institutional_ownership_pct"], 40.0) and m["eps_years_up_ratio"] == 1.0


def test_evaluate_marks_unknowns_not_pass_or_fail():
    rows = cl.evaluate(cl.metrics_from_yfinance({}, [], [], [], {}), cl.load_criteria())
    assert cl.summarize(rows)["확인 불가"] >= 5


def test_classification_heuristics():
    assert cl.classify("Technology", [3.0, 2.0], 30.0, 5.0)["category"] == "고성장주"
    assert cl.classify("Technology", [1.2, 1.0], 12.0, 3.0)["category"] == "우량주"
    assert cl.classify("Technology", [1.02, 1.0], 2.0, 3.0)["category"] == "저성장주"
    assert cl.classify("Energy", [1.2, 1.1], 8.0, 2.0)["category"].startswith("경기순환")
    assert cl.classify("Technology", [0.5, -0.2], None, 2.0)["category"] == "회생주"
    assert cl.classify("Financial Services", [1.0, 0.9], 5.0, 0.7)["category"].startswith("자산주")
    assert cl.classify("Technology", [], None, None)["category"] == "분류 불가"


def test_reference_is_derived_not_a_target():
    ref = cl.reference(100.0, 2.0, 15.0)
    assert ref["price_at_peg_1"] == 30.0 and "목표주가가 아닙니다" in ref["note"]
    assert cl.reference(100.0, 2.0, 300.0)["price_at_peg_1"] == 100.0  # 성장률 상한 50% 적용
    assert cl.reference(100.0, -1.0, 15.0)["price_at_peg_1"] is None


def test_system_prompt_has_guardrails_and_format():
    p = system_prompt()
    for must in ("AI 페르소나", "search_quotes", "find_similar_cases", "투자 조언이 아닙니다", "정확히 3줄", "🛒 **피터 린치** · AI 재현", "목표주가 아님", "지어내지"):
        assert must in p


def test_tools_wiring():
    assert TOOL_NAMES == ["mcp__lynch__search_quotes", "mcp__lynch__find_similar_cases", "mcp__lynch__get_known_facts", "mcp__lynch__get_lynch_checklist"]
    assert "[L" in search_quotes_impl("no_forecasting")
    assert "[K04]" in find_similar_cases_impl("소비재 생활 속 발견") and "사례가 있는 것처럼" in find_similar_cases_impl("zzzz qqqq")
    assert "1977" in known_facts_impl() and "미확인" in known_facts_impl()


def test_reference_gives_ratio_not_only_price():
    from lynch_agent import checklist as cl

    r = cl.reference(100.0, 4.0, 20.0)  # PEG 1 가격 = 4 × 20 = 80
    assert r["peg1_vs_price_pct"] == -20.0
