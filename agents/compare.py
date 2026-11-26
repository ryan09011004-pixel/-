"""한 티커를 다섯 에이전트의 점검표에 모두 대어 나란히 보여 준다(무료 Yahoo Finance, 모델 호출 없음).

사용: python compare.py NVDA
각 점검표의 기준값은 사람(인물)이 정한 숫자가 아니라 프로젝트 기본값이며, 결과는 결론이 아니라 질문거리다.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
AGENTS = [("buffett", "🎩 워런 버핏"), ("graham", "📘 벤저민 그레이엄"), ("lynch", "🛒 피터 린치"), ("dalio", "🧭 레이 달리오"), ("soros", "🌐 조지 소로스")]


def load_runner(agent: str) -> Callable[[str], dict[str, Any]]:
    sys.path.insert(0, str(ROOT / agent))
    try:
        return importlib.import_module(f"{agent}_agent.tools").checklist_impl
    finally:
        sys.path.remove(str(ROOT / agent))


def compare(ticker: str, runners: dict[str, Callable[[str], dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    """에이전트별 {agent, label, summary, failed, error}. 한 에이전트가 실패해도 나머지는 계속한다."""
    out = []
    for agent, label in AGENTS:
        row: dict[str, Any] = {"agent": agent, "label": label, "summary": None, "failed": [], "error": None}
        try:
            run = (runners or {}).get(agent) or load_runner(agent)
            res = run(ticker)
            row["summary"] = res["summary"]
            row["failed"] = [r["id"] for r in res["rows"] if r["result"] == "미달"]
        except Exception as e:  # 네트워크·티커 오류는 그 에이전트 칸에만 표시
            row["error"] = str(e)[:80]
        out.append(row)
    return out


def render(ticker: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"## {ticker.upper()} — 다섯 점검표 비교 (기준값은 프로젝트 기본값, 결론 아님)", "", "| 에이전트 | 통과 | 미달 | 확인 불가 | 미달 항목 |", "|---|---|---|---|---|"]
    for r in rows:
        if r["error"]:
            lines.append(f'| {r["label"]} | - | - | - | 점검 실패: {r["error"]} |')
        else:
            s = r["summary"]
            lines.append(f'| {r["label"]} | {s["통과"]} | {s["미달"]} | {s["확인 불가"]} | {", ".join(r["failed"]) or "-"} |')
    ok = [r for r in rows if not r["error"]]
    if ok:
        worst = max(ok, key=lambda r: r["summary"]["미달"])
        best = min(ok, key=lambda r: r["summary"]["미달"])
        lines += ["", f'미달이 가장 많은 관점: {worst["label"]}({worst["summary"]["미달"]}개), 가장 적은 관점: {best["label"]}({best["summary"]["미달"]}개). 관점이 갈리는 것은 자연스러운 일이며 어느 쪽도 투자 조언이 아닙니다.']
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    t = sys.argv[1].strip().upper()
    print(render(t, compare(t)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
