import re
from pathlib import Path

import pytest

from graham_agent import cases as cs


def test_cases_load_and_have_required_content():
    cc = cs.load_cases()
    assert len(cc) >= 8
    ids = [c.id for c in cc]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"K\d{2}", i) for i in ids)
    for c in cc:
        assert c.kind in cs.KINDS and c.lesson.strip() and c.sources
        assert c.evidence and all(e["text"].strip() and 1977 <= e["year"] <= 2024 for e in c.evidence)


def test_search_finds_relevant_cases():
    cc = cs.load_cases()
    assert "K01" in [c.id for c in cs.search(cc, "시장 변동 공포 때문에 팔아야 하나")]
    assert "K02" in [c.id for c in cs.search(cc, "안전마진 가격 싸게")]
    assert "K05" in [c.id for c in cs.search(cc, "보험 GEICO")]
    assert cs.search(cc, "zzzz qqqq") == []  # 관련 없으면 사례를 억지로 끼워 넣지 않는다


def test_case_evidence_matches_letters_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "1990.txt").exists():
        pytest.skip("원문 코퍼스 없음")
    import verify_quotes

    rows = verify_quotes.load_quotes(cs.PERSONA_DIR / "cases.jsonl")
    total, bad = verify_quotes.verify_cases(rows, corpus)
    assert total >= 13 and bad == []


def test_trap_question_set_is_well_formed():
    import json

    rows = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "evals" / "trap_questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)
    assert all(r["question"].strip() and r["expect"].strip() for r in rows)
    assert {"trap_fake_quote", "trap_prediction", "trap_directive", "format"} <= {r["kind"] for r in rows}
