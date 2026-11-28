"""투자 대가 패널: 에이전트별 근거 묶음을 만들고 답변 형식을 검사한다. 모델을 호출하지 않는다(비용 없음).

사용:
  python panel.py evidence <agent> "<질문>" [--ticker NVDA] [--market]   # 인용·사례·점검표·시장 배경을 JSON으로
  python panel.py check <agent> answer.txt                               # 3줄 형식·ID·가격 금액 검사
agent: buffett, graham, lynch, dalio, soros, all
이 근거로 답을 쓰는 것은 지금 대화 중인 Claude(.claude/skills/investor-panel)이며 별도 API 호출이 없다.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from common.format_check import HEADERS, check_answer  # noqa: E402
from common.market_context import PERSONA_USE  # noqa: E402

AGENTS = ["buffett", "graham", "lynch", "dalio", "soros"]


def tools_of(agent: str):
    sys.path.insert(0, str(ROOT / agent))
    try:
        return importlib.import_module(f"{agent}_agent.tools")
    finally:
        sys.path.remove(str(ROOT / agent))


def evidence(agent: str, question: str, ticker: str | None = None, market: dict[str, Any] | None = None) -> dict[str, Any]:
    t = tools_of(agent)
    out: dict[str, Any] = {
        "agent": agent,
        "header": HEADERS[agent],
        "system_prompt": str(ROOT / agent / "persona" / "system_prompt.md"),
        "quotes": t.search_quotes_impl(question),
        "cases": t.find_similar_cases_impl(question),
    }
    if ticker:
        try:
            out["checklist"] = t.checklist_impl(ticker)
        except Exception as e:  # 네트워크·티커 오류는 숨기지 않고 그대로 전달
            out["checklist"] = {"error": f"점검표를 만들지 못했습니다: {e}. 수치를 추측하지 마세요."}
    if market is not None:
        out["market_context"] = market | {"how_this_persona_uses_it": PERSONA_USE[agent]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evidence")
    e.add_argument("agent", choices=AGENTS + ["all"])
    e.add_argument("question")
    e.add_argument("--ticker")
    e.add_argument("--market", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("agent", choices=AGENTS)
    c.add_argument("file")
    c.add_argument("--one-line", action="store_true", help="범위 밖 질문 거절(머리글 + 한 줄)")
    a = ap.parse_args()
    if a.cmd == "check":
        text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
        problems = check_answer(a.agent, text, 1 if a.one_line else 3)
        print("형식 통과" if not problems else "\n".join(problems))
        return 0 if not problems else 1
    market = None
    if a.market:
        from common.market_context import fetch

        try:
            market = fetch()
        except Exception as ex:
            market = {"error": f"시장 배경을 가져오지 못했습니다: {ex}"}
    agents = AGENTS if a.agent == "all" else [a.agent]
    print(json.dumps([evidence(x, a.question, a.ticker, market) for x in agents], ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
