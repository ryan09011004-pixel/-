import re
from pathlib import Path

import pytest

from lynch_agent import quotes as qs


def test_quotes_load_and_ids_unique():
    qq = qs.load_quotes()
    assert len(qq) >= 15
    ids = [q.id for q in qq]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"L\d{2}", i) for i in ids)


def test_every_quote_has_interview_source_and_translation():
    for q in qs.load_quotes():
        assert q.url.startswith("https://www.pbs.org/") and q.doc == "frontline-1996" and q.year == 1996
        assert q.text.strip() and q.ko.strip()


def test_search_by_theme_and_keyword():
    qq = qs.load_quotes()
    nf = qs.search(qq, "no_forecasting")
    assert nf and all(x.theme == "no_forecasting" for x in nf)
    assert any("stomach" in x.text for x in qs.search(qq, "stomach"))
    assert qs.search(qq, "비트코인 폭등") == []


def test_quotes_match_original_interview_when_corpus_available():
    corpus = Path(__file__).resolve().parents[1] / "corpus" / "txt"
    if not (corpus / "frontline-1996.txt").exists():
        pytest.skip("원문 없음: python scripts/fetch_interview.py")
    import verify_quotes

    rows = verify_quotes.load_quotes(qs.PERSONA_DIR / "quotes.jsonl")
    assert verify_quotes.verify(rows, corpus) == []
