import json
import re
from pathlib import Path

import pytest

from soros_agent import cases as cs


def test_cases_load_and_have_required_content():
    cc = cs.load_cases()
    assert len(cc) >= 10
    ids = [c.id for c in cc]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"K\d{2}", i) for i in ids)
    for c in cc:
        assert c.kind in cs.KINDS and c.lesson.strip() and c.sources
        assert c.evidence and all(e["text"].strip() and e["doc"].startswith("soros-") for e in c.evidence)


def test_search_finds_relevant_cases():
    cc = cs.load_cases()
    assert "K01" in [c.id for c in cs.search(cc, "부동산 대출 담보 붐")]
    assert "K03" in [c.id for c in cs.search(cc, "버블 황혼 단계")]
    assert "K04" in [c.id for c in cs.search(cc, "효율적 시장 가설")]
    assert "K06" in [c.id for c in cs.search(cc, "환율 파동")]
    assert cs.search(cc, "zzzz qqqq") == []


def test_case_evidence_matches_sources_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "soros-essay-2014.txt").exists():
        pytest.skip("원문 없음: python scripts/fetch_sources.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(cs.PERSONA_DIR / "cases.jsonl")
    total, bad = verify_quotes.verify_cases(rows, corpus)
    assert total >= 12 and bad == []


def test_trap_question_set_is_well_formed():
    rows = [json.loads(l) for l in (Path(__file__).resolve().parents[1] / "evals" / "trap_questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) >= 10 and len({r["id"] for r in rows}) == len(rows)
    assert {"trap_fake_quote", "trap_prediction", "trap_directive", "format", "out_of_scope", "persona_identity"} <= {r["kind"] for r in rows}
