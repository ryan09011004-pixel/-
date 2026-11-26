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
LIST_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s")


def registry_ids(agent: str) -> set[str]:
    ids: set[str] = set()
    for name in ("quotes.jsonl", "cases.jsonl"):
        path = ROOT / agent / "persona" / name
        if path.exists():
            ids |= {json.loads(l)["id"] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    return ids


def check_answer(agent: str, text: str) -> list[str]:
    """문제 목록을 돌려준다. 빈 목록이면 형식 통과."""
    problems: list[str] = []
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return ["빈 답변"]
    if lines[0].strip() != HEADERS[agent]:
        problems.append(f"첫 줄 머리글이 다릅니다(기대: {HEADERS[agent]})")
    body = lines[1:]
    if len(body) != 3:
        problems.append(f"본문이 {len(body)}줄입니다(정확히 3줄이어야 함)")
    for i, l in enumerate(body, 1):
        if "(추정)" not in l:
            problems.append(f"{i}번째 줄에 '(추정)' 표시가 없습니다")
        if len(l) > MAX_LINE:
            problems.append(f"{i}번째 줄이 너무 깁니다({len(l)}자 > {MAX_LINE})")
        if LIST_RE.match(l) or l.lstrip().startswith(("#", ">", "|")):
            problems.append(f"{i}번째 줄에 목록·제목·표 형식이 있습니다")
    full = "\n".join(lines)
    if re.search(r"https?://", full):
        problems.append("링크가 들어 있습니다(원문은 사용자가 요청할 때만)")
    known = registry_ids(agent)
    for m in ID_RE.finditer(full):
        if m.group(1) not in known:
            problems.append(f"레지스트리에 없는 ID: [{m.group(1)}]")
        before, after = full[: m.start()], full[m.end():]
        if before.rfind("(") <= before.rfind(")") or after.find(")") == -1 or (after.find("(") != -1 and after.find("(") < after.find(")")):
            problems.append(f"ID [{m.group(1)}]는 괄호 안에만 써야 합니다")
    return problems
