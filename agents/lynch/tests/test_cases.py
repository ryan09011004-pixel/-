import json
import re
from pathlib import Path

import pytest

from lynch_agent import cases as cs


def test_cases_load_and_have_required_content():
    cc = cs.load_cases()
    assert len(cc) >= 12
    ids = [c.id for c in cc]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"K\d{2}", i) for i in ids)
    for c in cc:
        assert c.kind in cs.KINDS and c.lesson.strip() and c.sources
        assert c.evidence and all(e["text"].strip() and e.get("doc") == "frontline-1996" for e in c.evidence)


def test_library_includes_misses_and_scary_markets_not_only_wins():
    kinds = {c.id: c.kind for c in cs.load_cases()}
    assert kinds["K09"] == "mixed" and kinds["K05"] == "mixed" and kinds["K03"] == "mixed"  # 놓친 텐배거, 폭락, 회생 투자의 엇갈림


def test_search_finds_relevant_cases():
    cc = cs.load_cases()
    assert "K04" in [c.id for c in cs.search(cc, "생활 속에서 발견한 소비재 회사")]
    assert "K10" in [c.id for c in cs.search(cc, "언제 사야 하나 시장 타이밍")]
    assert "K03" in [c.id for c in cs.search(cc, "파산 위기 회생 종목")]
    assert cs.search(cc, "zzzz qqqq") == []


def test_case_evidence_matches_interview_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "frontline-1996.txt").exists():
        pytest.skip("원문 없음")
    import verify_quotes

    rows = verify_quotes.load_quotes(cs.PERSONA_DIR / "cases.jsonl")
    total, bad = verify_quotes.verify_cases(rows, corpus)
    assert total >= 20 and bad == []


def test_trap_question_set_is_well_formed():
    rows = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "evals" / "trap_questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)
    assert {"trap_fake_quote", "trap_prediction", "trap_directive", "format"} <= {r["kind"] for r in rows}
