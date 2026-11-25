import re
from pathlib import Path

import pytest

from graham_agent import quotes as qs


def test_quotes_load_and_ids_unique():
    qq = qs.load_quotes()
    assert len(qq) >= 10
    ids = [q.id for q in qq]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"G\d{2}", i) for i in ids)


def test_every_quote_has_letter_source_and_translation():
    for q in qs.load_quotes():
        assert q.url.startswith("https://www.berkshirehathaway.com/letters/")
        assert 1977 <= q.year <= 2024 and q.text.strip() and q.ko.strip()
        assert "Graham" in q.source or "Buffett" in q.source  # 그레이엄 직접 인용 또는 버핏의 요약임을 밝힌다


def test_search_by_theme_and_keyword():
    qq = qs.load_quotes()
    mos = qs.search(qq, "margin_of_safety")
    assert mos and all(x.theme == "margin_of_safety" for x in mos)
    assert any("Mr. Market" in x.text for x in qs.search(qq, "mr. market"))
    assert qs.search(qq, "비트코인 폭등") == []


def test_quotes_match_original_letters_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "1990.txt").exists():
        pytest.skip("원문 코퍼스 없음: ../buffett 에서 python scripts/fetch_letters.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(qs.PERSONA_DIR / "quotes.jsonl")
    assert verify_quotes.verify(rows, corpus) == []
