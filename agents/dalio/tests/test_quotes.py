import re
from pathlib import Path

import pytest

from dalio_agent import quotes as qs


def test_quotes_load_and_ids_unique():
    qq = qs.load_quotes()
    assert len(qq) >= 15
    ids = [q.id for q in qq]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"D\d{2}", i) for i in ids)


def test_every_quote_has_post_source_and_translation():
    for q in qs.load_quotes():
        assert q.url.startswith("https://raydalio.substack.com/p/") and q.doc.startswith("2026-") and q.year == 2026
        assert q.text.strip() and q.ko.strip()


def test_search_by_theme_and_keyword():
    qq = qs.load_quotes()
    nt = qs.search(qq, "no_market_timing")
    assert nt and all(x.theme == "no_market_timing" for x in nt)
    assert any("risk parity" in x.text for x in qs.search(qq, "risk parity"))
    assert qs.search(qq, "비트코인 폭등") == []


def test_quotes_match_original_posts_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not list(corpus.glob("2026-03-23-*.txt")):
        pytest.skip("원문 없음: python scripts/fetch_posts.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(qs.PERSONA_DIR / "quotes.jsonl")
    assert verify_quotes.verify(rows, corpus) == []
