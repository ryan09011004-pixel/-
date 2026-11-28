import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import panel  # noqa: E402
from common import market_context as mc  # noqa: E402

REPORT = {"composite": {"composite_score": 32.8, "zone": "Weakening", "guidance": "raise cash", "actions": ["Take profits"], "exposure_guidance": "40-60%", "strongest_health": {"label": "Level"}, "weakest_health": {"label": "Cycle"}, "data_quality": {"label": "Complete"}}, "components": {"ma_crossover": {"score": 35}, "divergence": 30.0}}


def test_market_summary_drops_trading_instructions():
    s = mc.summarize(REPORT)
    assert s["breadth_score"] == 32.8 and s["zone"] == "Weakening" and s["components"] == {"ma_crossover": 35, "divergence": 30.0}
    flat = str(s)
    assert "Take profits" not in flat and "raise cash" not in flat and "40-60%" not in flat
    assert s["dropped_from_skill"] == ["actions", "exposure_guidance", "guidance"]


def test_every_persona_has_market_usage_rule():
    assert set(mc.PERSONA_USE) == set(panel.AGENTS)


def test_evidence_offline_without_ticker():
    for a in panel.AGENTS:
        e = panel.evidence(a, "엔비디아 어떻게 생각해", market={"breadth_score": 50})
        assert e["header"] and "quotes" in e and "cases" in e and "checklist" not in e
        assert e["market_context"]["how_this_persona_uses_it"] == mc.PERSONA_USE[a]
    assert "C16" in panel.evidence("buffett", "엔비디아 어떻게 생각해")["cases"]
