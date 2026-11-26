"""결정 사례집: 버핏이 실제로 한 결정을 '상황 → 결정 → 본인이 밝힌 이유'로 정리한 persona/cases.jsonl."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .aliases import STOPWORDS, expand
from .quotes import PERSONA_DIR

REQUIRED_FIELDS = ("id", "title", "kind", "period", "situation", "decision", "reason", "lesson", "tags", "keywords", "evidence", "sources")
KINDS = {"success": "성공", "mistake": "실수", "mixed": "엇갈림", "rule": "규칙"}


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    kind: str
    period: str
    situation: str
    decision: str
    reason: str
    lesson: str
    tags: list[str]
    keywords: str
    evidence: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def render(self) -> str:
        ev = "\n".join(f'    - ({e["year"]}) "{e["text"]}"' for e in self.evidence)
        return (
            f"[{self.id}] {self.title} ({KINDS.get(self.kind, self.kind)}, {self.period})\n"
            f"  상황: {self.situation}\n  결정: {self.decision}\n  이유: {self.reason}\n  교훈: {self.lesson}\n"
            f"  원문 증거:\n{ev}"
        )


def load_cases(path: Path | None = None) -> list[Case]:
    path = path or PERSONA_DIR / "cases.jsonl"
    cases = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = [f for f in REQUIRED_FIELDS if f not in row]
        if missing:
            raise ValueError(f"{path.name}:{n} 필드 누락: {missing}")
        cases.append(Case(**{f: row[f] for f in REQUIRED_FIELDS}))
    return cases


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[\s,]+", text.lower()) if len(w) >= 2 and w not in STOPWORDS]


def search(cases: list[Case], query: str, limit: int = 3) -> list[Case]:
    """질문 속 단어가 태그·키워드·제목·상황·교훈에 많이 겹치는 사례를 고른다. 겹침이 없으면 빈 목록."""
    q = _words(expand(query))
    if not q:
        return []
    scored = []
    for c in cases:
        weighted = [(" ".join(c.tags).lower(), 3), (c.keywords.lower(), 3), (c.title.lower(), 2), (f"{c.situation} {c.lesson} {c.reason}".lower(), 1)]
        score = sum(w * sum(1 for token in q if token in text) for text, w in weighted)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda t: (-t[0], t[1].id))
    return [c for _, c in scored[:limit]]
