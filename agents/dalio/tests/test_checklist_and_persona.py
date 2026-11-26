import math

import numpy as np
import pytest

from dalio_agent import checklist as cl
from dalio_agent.agent import system_prompt
from dalio_agent.tools import TOOL_NAMES, find_similar_cases_impl, known_facts_impl, search_quotes_impl


def test_parse_portfolio_normalizes_and_validates():
    assert cl.parse_portfolio("SPY:30,TLT:40,GLD:30") == {"SPY": 0.3, "TLT": 0.4, "GLD": 0.3}
    assert cl.parse_portfolio("spy,tlt") == {"SPY": 0.5, "TLT": 0.5} and cl.parse_portfolio("NVDA") == {"NVDA": 1.0}
    for bad in ("", "SPY:-5", "SP Y:10", ",".join(f"T{i}" for i in range(13))):
        with pytest.raises(ValueError):
            cl.parse_portfolio(bad)


def test_categories():
    assert [cl.category(t) for t in ("SPY", "tlt", "GLD", "DBC", "TIP", "NVDA")] == ["주식", "채권", "물가대비", "물가대비", "물가대비", "주식"]


def _returns(seed=0, n=500):
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0004, 0.010, n)  # 저변동 자산
    b = rng.normal(0.0004, 0.020, n)  # 고변동 자산, a와 독립
    return np.column_stack([a, b])


def test_risk_contribution_sums_to_100_and_high_vol_dominates():
    m = cl.portfolio_metrics(_returns(), ["LOW", "HIGH"], [0.5, 0.5])
    assert math.isclose(sum(m["risk_contribution_pct"].values()), 100.0, abs_tol=0.5)
    assert m["risk_contribution_pct"]["HIGH"] > 70  # 돈은 50:50이어도 위험은 변동성 큰 쪽에 몰린다(달리오의 핵심 통찰)
    assert abs(m["avg_pairwise_correlation"]) < 0.2 and m["max_drawdown_pct"] <= 0


def test_inverse_vol_weights_balance_risk():
    w = cl.inverse_vol_weights({"LOW": 10.0, "HIGH": 20.0})
    assert w == {"LOW": 66.7, "HIGH": 33.3}
    assert cl.inverse_vol_weights({}) == {}


def test_single_asset_has_full_concentration_and_unknown_correlation():
    r = _returns()[:, :1]
    m = cl.portfolio_metrics(r, ["SOLO"], [1.0])
    assert math.isclose(m["max_risk_contribution_pct"], 100.0) and m["avg_pairwise_correlation"] is None
    rows = cl.evaluate(m, cl.load_criteria())
    assert {x["id"]: x["result"] for x in rows}["diversification"] == "확인 불가"


def test_balanced_vs_unbalanced_checklist():
    bal = cl.evaluate({"asset_count": 4.0, "max_risk_contribution_pct": 30.0, "avg_pairwise_correlation": 0.1, "inflation_hedge_weight_pct": 20.0, "bond_weight_pct": 30.0, "max_drawdown_pct": -10.0}, cl.load_criteria())
    assert cl.summarize(bal) == {"통과": 6, "미달": 0, "확인 불가": 0}
    unb = cl.evaluate({"asset_count": 2.0, "max_risk_contribution_pct": 76.0, "avg_pairwise_correlation": 0.1, "inflation_hedge_weight_pct": 0.0, "bond_weight_pct": 40.0, "max_drawdown_pct": -12.0}, cl.load_criteria())
    assert cl.summarize(unb)["미달"] == 3


def test_environment_correlations():
    a = np.array([0.01, -0.02, 0.03, 0.0, 0.01])
    out = cl.environment_correlations(a, {"SAME": a, "OPP": -a})
    assert out == {"SAME": 1.0, "OPP": -1.0}


def test_system_prompt_has_guardrails_and_format():
    p = system_prompt()
    for must in ("비공식 AI 페르소나", "공식 \"AI 클론\"", "search_quotes", "find_similar_cases", "투자 조언이 아닙니다", "정확히 3줄", "🧭 **레이 달리오** · AI 재현(비공식)", "변동성 역수", "지어내지"):
        assert must in p


def test_tools_wiring():
    assert TOOL_NAMES == ["mcp__dalio__search_quotes", "mcp__dalio__find_similar_cases", "mcp__dalio__get_known_facts", "mcp__dalio__get_dalio_checklist"]
    assert "[D" in search_quotes_impl("no_market_timing")
    assert "[K02]" in find_similar_cases_impl("리스크 패리티 변동성") and "사례가 있는 것처럼" in find_similar_cases_impl("zzzz qqqq")
    f = known_facts_impl()
    assert "AI 클론" in f and "미확인" in f and "비공식" in f
