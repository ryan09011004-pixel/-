import re
from pathlib import Path

import pytest

from soros_agent import quotes as qs


def test_quotes_load_and_ids_unique():
    qq = qs.load_quotes()
    assert len(qq) >= 20
    ids = [q.id for q in qq]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"S\d{2}", i) for i in ids)


def test_every_quote_has_known_source_and_translation():
    for q in qs.load_quotes():
        assert q.doc in ("soros-essay-2014", "soros-lecture-2009") and q.year in (2009, 2013)
        assert q.url.startswith(("https://www.georgesoros.com/", "https://www.opensocietyfoundations.org/"))
        assert q.text.strip() and q.ko.strip()


def test_search_by_theme_and_keyword():
    qq = qs.load_quotes()
    bb = qs.search(qq, "boom_bust")
    assert bb and all(x.theme == "boom_bust" for x in bb)
    assert any("Siamese" in x.text for x in qs.search(qq, "Siamese twins"))
    assert qs.search(qq, "비트코인 폭등") == []


def test_quotes_match_original_texts_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "soros-essay-2014.txt").exists():
        pytest.skip("원문 없음: python scripts/fetch_sources.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(qs.PERSONA_DIR / "quotes.jsonl")
    assert verify_quotes.verify(rows, corpus) == []
