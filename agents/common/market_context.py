"""시장 전체 배경: 설치된 market-breadth-analyzer 스킬(TraderMonty 공개 CSV, 키·비용 없음)을 돌려 '참여 폭' 점수만 꺼낸다.

스킬이 내놓는 매매 행동 지침(actions, exposure_guidance, guidance)은 페르소나에 넘기지 않는다.
페르소나 지침이 매수·매도 지시를 금지하기 때문이다. 점수는 배경 정보이며 예측이 아니다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".claude" / "skills" / "market-breadth-analyzer" / "scripts" / "market_breadth_analyzer.py"
DROP = {"actions", "exposure_guidance", "guidance"}
PERSONA_USE = {
    "buffett": "시장 타이밍 근거로 쓰지 않습니다. 남들이 두려워하는지 탐욕스러운지의 배경으로만 한 구절 언급할 수 있습니다.",
    "graham": "시장 씨의 기분을 보여 주는 배경일 뿐 가치 판단의 근거가 아닙니다.",
    "lynch": "시장 예측에 쓰지 않습니다. 회사 이야기와 숫자가 먼저입니다.",
    "dalio": "지금 어떤 환경에 가까운지의 배경으로만 씁니다. 배분을 바꾸는 근거로 삼지 않습니다.",
    "soros": "추세가 넓게 퍼졌는지(되먹임의 폭)를 보는 배경 신호로 씁니다. 단계 판정을 확정하는 근거는 아닙니다.",
}


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    comp = report.get("composite", {})
    return {
        "breadth_score": comp.get("composite_score"),
        "zone": comp.get("zone"),
        "components": {k: (v.get("score") if isinstance(v, dict) else v) for k, v in report.get("components", {}).items()},
        "strongest": (comp.get("strongest_health") or {}).get("label"),
        "weakest": (comp.get("weakest_health") or {}).get("label"),
        "data_quality": (comp.get("data_quality") or {}).get("label"),
        "source": "market-breadth-analyzer 스킬(TraderMonty 공개 CSV, S&P 500 참여 폭, 키·비용 없음)",
        "note": "0~100, 높을수록 많은 종목이 함께 오르는 건강한 상태. 배경 정보이며 예측·매매 지시가 아닙니다.",
        "dropped_from_skill": sorted(DROP & set(comp)),
    }


def fetch() -> dict[str, Any]:
    if not SCRIPT.exists():
        raise FileNotFoundError(f"스킬 스크립트가 없습니다: {SCRIPT}")
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, str(SCRIPT), "--output-dir", d], check=True, capture_output=True, text=True, timeout=180)
        files = sorted(Path(d).glob("market_breadth_2*.json"))
        if not files:
            raise RuntimeError("스킬이 보고서를 만들지 못했습니다(tradermonty.github.io 접근 필요).")
        return summarize(json.loads(files[-1].read_text(encoding="utf-8")))
