import re
from pathlib import Path

import pytest

from buffett_agent import cases as cs


def test_cases_load_and_have_required_content():
    cc = cs.load_cases()
    assert len(cc) >= 15
    ids = [c.id for c in cc]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"C\d{2}", i) for i in ids)
    for c in cc:
        assert c.kind in cs.KINDS
        assert c.evidence and all(e["text"].strip() and 1977 <= e["year"] <= 2024 for e in c.evidence)
        assert c.lesson.strip() and c.sources


def test_library_is_balanced_not_only_successes():
    kinds = [c.kind for c in cs.load_cases()]
    assert kinds.count("mistake") >= 4 and kinds.count("success") >= 5  # 실수 사례도 충분히 포함


def test_search_finds_relevant_cases():
    cc = cs.load_cases()
    assert "C13" in [c.id for c in cs.search(cc, "애플 같은 기술주를 어떻게 보나")]
    assert {"C05"} & {c.id for c in cs.search(cc, "항공사 주식")}
    assert {"C14"} & {c.id for c in cs.search(cc, "초보는 인덱스 펀드")}
    assert cs.search(cc, "zzzz qqqq") == []  # 관련 없으면 사례를 억지로 끼워 넣지 않는다


def test_case_evidence_matches_letters_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not corpus.exists():
        pytest.skip("원문 코퍼스 없음: python scripts/fetch_letters.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(cs.PERSONA_DIR / "cases.jsonl")
    total, bad = verify_quotes.verify_cases(rows, corpus)
    assert total >= 25 and bad == []
