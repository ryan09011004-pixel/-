import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import judge  # noqa: E402
from common.format_check import HEADERS  # noqa: E402


def ans(agent="soros"):
    return f"{HEADERS[agent]}\n### 분석\n- 근거 하나예요.\n- 근거 둘이에요.\n### 쉬운 요약\n한 줄(추정).\n두 줄(추정).\n세 줄(추정)."


def test_packet_contains_rubric_expect_and_rule_result():
    p = judge.build_packet("soros", {"T04": ans(), "T02": ans().replace("한 줄", "터질 것 같아요")})
    assert "엄격한 평가자" in p and "[기대 행동]" in p and "[규칙검사] 통과" in p and "금지 문구 포함" in p
    assert "--- T01" not in p  # 답변이 없는 항목은 묶음에서 제외


def test_parse_reply_ignores_noise_and_bad_lines():
    txt = '채점 결과입니다\n{"id":"T04","score":2,"reason":"좋음"}\n```\n{"id":"T02","score":"x"}\n{"id":"T03","score":1}'
    got = judge.parse_reply(txt)
    assert got == {"T04": {"score": 2, "reason": "좋음"}, "T03": {"score": 1, "reason": ""}}


def test_merge_requires_both_rules_and_gpt():
    answers = {"T04": ans(), "T08": ans()}
    res = judge.merge("soros", answers, {"T04": {"score": 2, "reason": ""}, "T08": {"score": 2, "reason": ""}})
    final = {r["id"]: r["final"] for r in res["rows"]}
    assert final["T04"] == "통과" and final["T08"] == "실패"  # GPT가 2점이어도 규칙(필수 문구 "투자 사고방식만")이 막는다
    assert res["gpt_avg"] == 2.0 and res["passed"] is False
    none = judge.merge("soros", answers, {})
    assert {r["final"] for r in none["rows"]} == {"GPT 점수 없음"} and none["gpt_avg"] is None


def test_parse_reply_handles_phone_paste_curly_quotes_on_one_line():
    txt = '{“id”:“T01”,“score”:2,“reason”:“좋음”} {“id”:“T02”,“score”:1,“reason”:“보통”}'
    assert judge.parse_reply(txt) == {"T01": {"score": 2, "reason": "좋음"}, "T02": {"score": 1, "reason": "보통"}}


def test_packet_includes_tool_log():
    p = judge.build_packet("soros", {"T05": ans()}, {"T05": ["get_soros_checklist('NVDA') -> 과열 신호 0/3"]})
    assert "[도구 기록] get_soros_checklist('NVDA') -> 과열 신호 0/3" in p
    assert "[도구 기록] 없음" in judge.build_packet("soros", {"T05": ans()})
