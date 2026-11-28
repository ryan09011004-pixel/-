"""에이전트 답변이 약속한 형식을 지켰는지 검사한다(오프라인, 비용 없음).

형식: 첫 줄 머리글, 그 아래 정확히 3줄, 각 줄에 '(추정)', 인용·사례 ID는 실제 레지스트리에 있는 것만,
표·목록·링크·제목 마크다운 없음. 사용자가 사전에 승인한 3줄 대화 형식을 기계적으로 지키게 하려는 장치다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {
    "buffett": "🎩 **워런버핏** · AI 재현",
    "graham": "📘 **벤저민 그레이엄** · AI 재현",
    "lynch": "🛒 **피터 린치** · AI 재현",
    "dalio": "🧭 **레이 달리오** · AI 재현(비공식)",
    "soros": "🌐 **조지 소로스** · AI 재현(비공식)",
}
MAX_LINE = 220
ID_RE = re.compile(r"\[([A-Z]\d{2})\]")
PRICE_RE = re.compile(r"\$\s?\d|\d[\d,.]*\s*(달러|원)")
REACH_RE = re.compile(r"(되찾|도달|닿으|올라서|넘어서면|돌파)")
LIST_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s")


def registry_ids(agent: str) -> set[str]:
    ids: set[str] = set()
    for name in ("quotes.jsonl", "cases.jsonl"):
        path = ROOT / agent / "persona" / name
        if path.exists():
            ids |= {json.loads(l)["id"] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    return ids


SUMMARY_RE = re.compile(r"^#{0,4}\s*\**\s*쉬운 요약\s*\**\s*$")
ANALYSIS_RE = re.compile(r"^#{0,4}\s*\**\s*분석\s*\**\s*$")
MAX_ANALYSIS = 12


def _common_checks(agent: str, lines: list[str], scan: list[str], problems: list[str]) -> None:
    full = "\n".join(lines)
    if PRICE_RE.search(full):
        problems.append("가격 숫자(달러·원)가 있습니다(현재가 대비 비율로 써야 함)")
    for l in scan:
        if "%" in l and REACH_RE.search(l) and ("선" in l or "가격" in l or "고점" in l or "저점" in l):
            problems.append(f"가격 도달 조건이 있습니다(근거 신호로 써야 함): {l[:30]}")
    if re.search(r"https?://", full):
        problems.append("링크가 들어 있습니다(원문은 사용자가 요청할 때만)")
    known = registry_ids(agent)
    for m in ID_RE.finditer(full):
        if m.group(1) not in known:
            problems.append(f"레지스트리에 없는 ID: [{m.group(1)}]")
        before, after = full[: m.start()], full[m.end():]
        if before.rfind("(") <= before.rfind(")") or after.find(")") == -1 or (after.find("(") != -1 and after.find("(") < after.find(")")):
            problems.append(f"ID [{m.group(1)}]는 괄호 안에만 써야 합니다")


def check_answer(agent: str, text: str, body_lines: int = 3) -> list[str]:
    """문제 목록을 돌려준다. 빈 목록이면 형식 통과.

    기본 구조(2026-11-28 사용자 결정): 머리글 → '### 분석'(정확한 분석, 목록 허용) → 맨 아래 '### 쉬운 요약'(정확히 3줄, 각 줄 (추정)).
    범위 밖 질문은 body_lines=1: 머리글 + 거절 한 줄만.
    """
    problems: list[str] = []
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return ["빈 답변"]
    if lines[0].strip() != HEADERS[agent]:
        problems.append(f"첫 줄 머리글이 다릅니다(기대: {HEADERS[agent]})")
    if body_lines == 1:
        body = lines[1:]
        if len(body) != 1:
            problems.append(f"본문이 {len(body)}줄입니다(정확히 1줄이어야 함)")
        _common_checks(agent, lines, body, problems)
        return problems
    idx = next((i for i, l in enumerate(lines) if SUMMARY_RE.match(l.strip())), None)
    if idx is None:
        problems.append("맨 아래 '### 쉬운 요약' 부분이 없습니다")
        _common_checks(agent, lines, lines[1:], problems)
        return problems
    analysis = [l for l in lines[1:idx] if not ANALYSIS_RE.match(l.strip())]
    summary = lines[idx + 1:]
    if not any(ANALYSIS_RE.match(l.strip()) for l in lines[1:idx]):
        problems.append("'### 분석' 제목이 없습니다")
    if not 2 <= len(analysis) <= MAX_ANALYSIS:
        problems.append(f"분석이 {len(analysis)}줄입니다(2~{MAX_ANALYSIS}줄)")
    if len(summary) != 3:
        problems.append(f"쉬운 요약이 {len(summary)}줄입니다(정확히 3줄이어야 함)")
    for i, l in enumerate(summary, 1):
        if "(추정)" not in l:
            problems.append(f"요약 {i}번째 줄에 '(추정)' 표시가 없습니다")
        if len(l) > MAX_LINE:
            problems.append(f"요약 {i}번째 줄이 너무 깁니다({len(l)}자 > {MAX_LINE})")
        if LIST_RE.match(l) or l.lstrip().startswith(("#", ">", "|")):
            problems.append(f"요약 {i}번째 줄에 목록·제목·표 형식이 있습니다")
    _common_checks(agent, lines, analysis + summary, problems)
    return problems
