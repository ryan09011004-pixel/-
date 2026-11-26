import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import compare as cmp  # noqa: E402


def fake(passed, failed, unknown=0, ids=()):
    rows = [{"id": i, "result": "미달"} for i in ids] + [{"id": f"ok{n}", "result": "통과"} for n in range(passed)]
    return lambda t: {"summary": {"통과": passed, "미달": failed, "확인 불가": unknown}, "rows": rows}


def boom(t):
    raise ValueError("가격 데이터가 부족합니다")


def test_compare_tolerates_one_failing_agent_and_renders_table():
    runners = {"buffett": fake(5, 2, ids=("pe", "debt")), "graham": fake(3, 4, ids=("a", "b", "c", "d")), "lynch": boom, "dalio": fake(6, 0), "soros": fake(4, 2, ids=("vol_regime", "drawdown_now"))}
    rows = cmp.compare("nvda", runners)
    assert [r["agent"] for r in rows] == ["buffett", "graham", "lynch", "dalio", "soros"]
    assert rows[2]["error"] and rows[0]["failed"] == ["pe", "debt"]
    text = cmp.render("nvda", rows)
    assert "NVDA" in text and "점검 실패" in text and "투자 조언이 아닙니다" in text
    assert "벤저민 그레이엄(4개)" in text and "레이 달리오(0개)" in text


def test_all_failing_does_not_crash():
    runners = {a: boom for a, _ in cmp.AGENTS}
    text = cmp.render("x", cmp.compare("x", runners))
    assert text.count("점검 실패") == 5 and "미달이 가장 많은" not in text
