import re
from pathlib import Path

import pytest

from buffett_agent import quotes as qs


def test_quotes_load_and_ids_unique():
    qq = qs.load_quotes()
    assert len(qq) >= 25
    ids = [q.id for q in qq]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"Q\d{2}", i) for i in ids)


def test_every_quote_has_primary_source_and_translation():
    for q in qs.load_quotes():
        assert q.url.startswith("https://www.berkshirehathaway.com/letters/")
        assert 1977 <= q.year <= 2024  # 2025년분은 에이블이 쓴 서한이라 버핏 인용에 쓰지 않는다
        assert q.text.strip() and q.ko.strip()


def test_search_by_theme_and_keyword():
    qq = qs.load_quotes()
    moat = qs.search(qq, "moat")
    assert moat and all(x.theme == "moat" for x in moat)
    assert any("Mr. Market" in x.text for x in qs.search(qq, "mr. market"))
    assert qs.search(qq, "비트코인 폭등") == []  # 근거 없으면 빈 결과


def test_quotes_match_original_letters_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not corpus.exists():
        pytest.skip("원문 코퍼스 없음: python scripts/fetch_letters.py 로 내려받으면 검증한다")
    import verify_quotes

    rows = verify_quotes.load_quotes(qs.PERSONA_DIR / "quotes.jsonl")
    assert verify_quotes.verify(rows, corpus) == []
