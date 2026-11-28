import numpy as np

from soros_agent import checklist as cl
from soros_agent.agent import system_prompt
from soros_agent.tools import TOOL_NAMES, find_similar_cases_impl, known_facts_impl, search_quotes_impl


def _series(kind: str, n: int = 600) -> np.ndarray:
    if kind == "flat":
        return 100 + np.sin(np.linspace(0, 20, n))  # 제자리 진동
    if kind == "boom":  # 1년 전까지 횡보 → 9개월 완만한 상승 → 마지막 분기 급등(가속)
        rng = np.random.default_rng(1)
        base = np.concatenate([np.full(n - 252, 100.0), np.linspace(100, 180, 189), np.linspace(180, 300, 63)])
        return base * np.exp(rng.normal(0, 0.004, n))
    if kind == "bust":  # 오르다 고점 후 급락
        up = 100 * np.exp(np.linspace(0, 1.2, n - 120))
        return np.concatenate([up, up[-1] * np.exp(-np.linspace(0, 0.9, 120))])
    raise ValueError(kind)


def test_metrics_flat_series_is_quiet():
    m = cl.metrics_from_prices(_series("flat"))
    assert abs(m["ret_12m_pct"]) < 5 and abs(m["ext_vs_200d_pct"]) < 5 and m["drawdown_from_peak_pct"] > -5


def test_metrics_boom_flags_overheat():
    m = cl.metrics_from_prices(_series("boom"))
    assert m["ret_12m_pct"] > 100 and m["ext_vs_200d_pct"] > 40 and m["acceleration_pp"] > 25
    rows = cl.evaluate(m, cl.load_criteria())
    got = {r["id"]: r["result"] for r in rows}
    assert got["run_up_12m"] == got["extension_200d"] == got["acceleration"] == "미달"
    assert cl.classify_stage(m)["stage"] in ("가속·과열 의심", "황혼 의심")


def test_bust_is_classified_as_collapse():
    m = cl.metrics_from_prices(_series("bust"))
    assert m["drawdown_from_peak_pct"] < -20 and m["ext_vs_200d_pct"] < 0
    assert cl.classify_stage(m)["stage"] == "붕괴 의심"


def test_short_history_returns_unknowns_not_guesses():
    m = cl.metrics_from_prices(np.linspace(100, 110, 100))
    assert m["ret_12m_pct"] is None and m["acceleration_pp"] is None
    rows = cl.evaluate(m, cl.load_criteria())
    assert {r["id"]: r["result"] for r in rows}["run_up_12m"] == "확인 불가"
    assert cl.classify_stage(cl.metrics_from_prices(np.linspace(100, 110, 20)))["stage"] == "판정 불가"


def test_reference_levels_are_not_targets():
    lv = cl.reference_levels(_series("flat"))
    assert {"last_close", "ma50", "ma200", "high_3y", "low_3y", "ma200_vs_price_pct"} <= set(lv) and lv["ma200"] is not None


def test_summarize_counts():
    rows = cl.evaluate(cl.metrics_from_prices(_series("boom")), cl.load_criteria())
    s = cl.summarize(rows)
    assert sum(s.values()) == 6 and s["미달"] >= 3


def test_system_prompt_has_guardrails_and_format():
    p = system_prompt()
    for must in ("비공식 AI 페르소나", "search_quotes", "find_similar_cases", "투자 조언이 아닙니다", "정확히 3줄", "🌐 **조지 소로스** · AI 재현(비공식)", "미확인", "가설", "지어내지", "투자 사고방식만"):
        assert must in p


def test_tools_wiring():
    assert TOOL_NAMES == ["mcp__soros__search_quotes", "mcp__soros__find_similar_cases", "mcp__soros__get_known_facts", "mcp__soros__get_soros_checklist"]
    assert "[S" in search_quotes_impl("boom_bust")
    assert "[K03]" in find_similar_cases_impl("버블 황혼") and "사례가 있는 것처럼" in find_similar_cases_impl("zzzz qqqq")
    f = known_facts_impl()
    assert "1992" in f and "미확인" in f and "비공식" in f


def test_reference_levels_include_ratios_to_price():
    lv = cl.reference_levels(np.concatenate([np.full(200, 100.0), [80.0]]))
    assert lv["ma200_vs_price_pct"] == round((lv["ma200"] / 80.0 - 1) * 100, 1) and lv["high_3y_vs_price_pct"] == 25.0
