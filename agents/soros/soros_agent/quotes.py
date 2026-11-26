"""검증된 인용 레지스트리: persona/quotes.jsonl을 읽고 검색한다."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .aliases import expand

PERSONA_DIR = Path(__file__).resolve().parents[1] / "persona"
REQUIRED_FIELDS = ("id", "theme", "year", "source", "url", "text", "ko")


@dataclass(frozen=True)
class Quote:
    id: str
    theme: str
    year: int
    source: str
    url: str
    text: str
    ko: str
    doc: str = ""  # 보도자료 등 연도만으로 원문 파일을 정할 수 없을 때의 코퍼스 문서 이름

    def render(self) -> str:
        return f'[{self.id}] "{self.text}" ({self.source})\n  번역: {self.ko}\n  원문: {self.url}'


def load_quotes(path: Path | None = None) -> list[Quote]:
    path = path or PERSONA_DIR / "quotes.jsonl"
    quotes = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = [f for f in REQUIRED_FIELDS if f not in row]
        if missing:
            raise ValueError(f"{path.name}:{n} 필드 누락: {missing}")
        quotes.append(Quote(**{f: row[f] for f in REQUIRED_FIELDS}, doc=row.get("doc", "")))
    return quotes


def themes(quotes: list[Quote]) -> list[str]:
    return sorted({q.theme for q in quotes})


def search(quotes: list[Quote], query: str, limit: int = 6) -> list[Quote]:
    """주제 이름이 정확히 같으면 그 주제 전체, 아니면 영어 원문·번역에서 단어를 찾는다."""
    q = query.strip().lower()
    if not q:
        return []
    by_theme = [x for x in quotes if x.theme == q]
    if by_theme:
        return by_theme[:limit]
    words = [w for w in expand(q).replace(",", " ").split() if w]
    scored = []
    for x in quotes:
        hay = f"{x.theme} {x.text} {x.ko}".lower()
        score = sum(hay.count(w) for w in words)
        if score:
            scored.append((score, x))
    scored.sort(key=lambda t: (-t[0], t[1].id))
    return [x for _, x in scored[:limit]]
