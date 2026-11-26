import json
import re
from pathlib import Path

import pytest

from dalio_agent import cases as cs


def test_cases_load_and_have_required_content():
    cc = cs.load_cases()
    assert len(cc) >= 12
    ids = [c.id for c in cc]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"K\d{2}", i) for i in ids)
    for c in cc:
        assert c.kind in cs.KINDS and c.lesson.strip() and c.sources
        assert c.evidence and all(e["text"].strip() and e["doc"].startswith("2026-") for e in c.evidence)


def test_search_finds_relevant_cases():
    cc = cs.load_cases()
    assert "K02" in [c.id for c in cc and cs.search(cc, "리스크 패리티 변동성 균형")]
    assert "K03" in [c.id for c in cs.search(cc, "현금이 안전한가요 인플레이션")]
    assert "K05" in [c.id for c in cs.search(cc, "금 안전자산")]
    assert "K08" in [c.id for c in cs.search(cc, "반대 의견 스트레스 테스트")]
    assert cs.search(cc, "zzzz qqqq") == []


def test_case_evidence_matches_posts_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not list(corpus.glob("2026-03-23-*.txt")):
        pytest.skip("원문 없음")
    import verify_quotes

    rows = verify_quotes.load_quotes(cs.PERSONA_DIR / "cases.jsonl")
    total, bad = verify_quotes.verify_cases(rows, corpus)
    assert total >= 15 and bad == []


def test_trap_question_set_is_well_formed():
    rows = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "evals" / "trap_questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)
    assert {"trap_fake_quote", "trap_prediction", "trap_directive", "format", "official_clone"} <= {r["kind"] for r in rows}
