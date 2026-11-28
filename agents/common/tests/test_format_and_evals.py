import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import format_check as fc  # noqa: E402
from common import score_evals as se  # noqa: E402

AGENTS = sorted(fc.HEADERS)


def good(agent: str, qid: str, cid: str) -> str:
    return (
        f"{fc.HEADERS[agent]}\n"
        f"지금은 정보가 더 필요해 보여요(추정) ({qid}).\n"
        f"숫자 하나가 기준 안으로 들어오면 살펴볼 만해요(추정) ({cid}).\n"
        "기준을 벗어나면 줄이는 쪽으로 생각해요(추정)."
    )


FIRST = {a: {j: next(l for l in (ROOT / a / "persona" / n).read_text(encoding="utf-8").splitlines() if l.strip()) for j, n in (("q", "quotes.jsonl"), ("c", "cases.jsonl"))} for a in AGENTS}


def ids(agent):
    return json.loads(FIRST[agent]["q"])["id"], json.loads(FIRST[agent]["c"])["id"]


@pytest.mark.parametrize("agent", AGENTS)
def test_good_answer_passes(agent):
    q, c = ids(agent)
    assert fc.check_answer(agent, good(agent, q, c)) == []


@pytest.mark.parametrize("agent", AGENTS)
def test_bad_answers_are_caught(agent):
    q, c = ids(agent)
    ok = good(agent, q, c)
    lines = ok.splitlines()
    assert any("머리글" in p for p in fc.check_answer(agent, "\n".join(lines[1:])))  # 머리글 없음
    assert any("3줄" in p for p in fc.check_answer(agent, "\n".join(lines + ["넷째 줄(추정)"])))
    assert any("(추정)" in p for p in fc.check_answer(agent, ok.replace("(추정)", "", 1)))
    assert any("레지스트리" in p for p in fc.check_answer(agent, ok.replace(f"({q})", "([Z99])")))
    assert any("목록" in p for p in fc.check_answer(agent, "\n".join(lines[:1] + ["- " + lines[1]] + lines[2:])))
    assert any("링크" in p for p in fc.check_answer(agent, ok + " https://example.com"))
    assert any("괄호" in p for p in fc.check_answer(agent, ok.replace(f"({q})", f"[{q}]")))


@pytest.mark.parametrize("agent", AGENTS)
def test_header_matches_system_prompt(agent):
    prompt = (ROOT / agent / "persona" / "system_prompt.md").read_text(encoding="utf-8")
    assert fc.HEADERS[agent] in prompt


@pytest.mark.parametrize("agent", AGENTS)
def test_eval_set_is_complete_and_scoreable(agent):
    rows = se.load_evals(agent)
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert {"id", "kind", "question", "expect", "must_include", "must_not_include"} <= set(r)
    q, c = ids(agent)
    answers = {r["id"]: good(agent, q, c) for r in rows}
    result = se.score(agent, answers)
    # 형식은 통과하지만 필수 문구 규칙이 있는 질문은 일부러 실패해야 한다(규칙이 실제로 작동하는지 확인)
    assert all(not any("머리글" in p or "3줄" in p for p in r["problems"]) for r in result if r["kind"] != "out_of_scope")
    assert any(r["result"] == "실패" for r in result) or all(not q_["must_include"] for q_ in rows)
    bad = se.score(agent, {})
    assert {r["result"] for r in bad} == {"답변 없음"}


def test_forbidden_phrase_rule_works():
    q, c = ids("soros")
    ans = good("soros", q, c).replace("정보가 더 필요해 보여요", "터질 것 같아요")
    r = {x["id"]: x for x in se.score("soros", {"T02": ans})}["T02"]
    assert r["result"] == "실패" and any("금지 문구" in p for p in r["problems"])


def test_out_of_scope_allows_single_refusal_line():
    one = f"{fc.HEADERS['soros']}\n그 질문은 다루지 않아요, 이 페르소나는 투자 사고방식만 다뤄요."
    assert fc.check_answer("soros", one, body_lines=1) == []
    assert any("1줄" in p for p in fc.check_answer("soros", one + "\n덧붙인 설명(추정).", body_lines=1))
    r = {x["id"]: x for x in se.score("soros", {"T08": one})}["T08"]
    assert r["result"] == "통과"


@pytest.mark.parametrize("agent", AGENTS)
def test_prompts_have_grading_feedback_rules(agent):
    p = (ROOT / agent / "persona" / "system_prompt.md").read_text(encoding="utf-8")
    assert "표현 규칙 (2026-11-28" in p and "다시 따져 볼 신호" in p and "점검표 기준" in p and "도달 조건" in p


@pytest.mark.parametrize("agent", AGENTS)
def test_price_amounts_are_flagged_but_ratios_pass(agent):
    q, c = ids(agent)
    ok = good(agent, q, c)
    assert any("가격 숫자" in p for p in fc.check_answer(agent, ok.replace("숫자 하나가", "약 202달러가")))
    assert any("가격 숫자" in p for p in fc.check_answer(agent, ok.replace("숫자 하나가", "$150이")))
    assert any("도달 조건" in p for p in fc.check_answer(agent, ok.replace("숫자 하나가", "지금보다 35% 위인 200일선을 되찾는 게")))
    assert fc.check_answer(agent, ok.replace("숫자 하나가", "출렁임이 평소의 1.57배보다 커지는 게")) == []
    assert "가격 수준을 조건으로 쓰지 않습니다" in (ROOT / agent / "persona" / "system_prompt.md").read_text(encoding="utf-8")
