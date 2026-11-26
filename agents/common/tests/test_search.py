import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ["buffett", "graham", "lynch", "dalio", "soros"]
sys.path.insert(0, str(ROOT))


def load(agent: str):
    sys.path.insert(0, str(ROOT / agent))
    try:
        return importlib.import_module(f"{agent}_agent.cases"), importlib.import_module(f"{agent}_agent.quotes")
    finally:
        sys.path.remove(str(ROOT / agent))


def test_alias_copies_are_identical():
    src = (ROOT / "common" / "aliases.py").read_text(encoding="utf-8")
    for a in AGENTS:
        assert (ROOT / a / f"{a}_agent" / "aliases.py").read_text(encoding="utf-8") == src, a


def test_expand_adds_keywords_only_for_known_terms():
    from common.aliases import expand

    assert "technology" in expand("엔비디아 어떻게 생각해") and "tech" in expand("NVDA")
    assert expand("비트코인") == "비트코인" and expand("zzzz qqqq") == "zzzz qqqq"
    assert "gold" in expand("금 사야 하나") and "gold" not in expand("지금 금융위기가 올까")


@pytest.mark.parametrize("agent", AGENTS)
def test_unknown_topics_return_nothing(agent):
    cs, qs = load(agent)
    assert cs.search(cs.load_cases(), "비트코인") == [] and cs.search(cs.load_cases(), "zzzz qqqq") == []
    assert qs.search(qs.load_quotes(), "비트코인 폭등") == []


def test_buffett_tech_query_returns_both_sides():
    cs, _ = load("buffett")
    ids = [c.id for c in cs.search(cs.load_cases(), "엔비디아 어떻게 생각해")]
    assert {"C13", "C16"} <= set(ids)  # 애플을 산 사례와 기술을 피하는 규칙이 함께 나온다


def test_stopwords_do_not_pull_random_cases():
    cs, _ = load("buffett")
    assert "C06" not in [c.id for c in cs.search(cs.load_cases(), "금 지금 사야 하나")]
