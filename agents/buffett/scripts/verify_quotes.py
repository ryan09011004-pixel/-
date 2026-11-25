"""persona/quotes.jsonl의 모든 인용이 해당 연도 주주서한 원문에 그대로 있는지 검증한다.

사용: python scripts/verify_quotes.py [--corpus corpus/txt]
실패가 하나라도 있으면 종료 코드 1. 원문과 다르면 레지스트리에 넣지 않는다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(s: str) -> str:
    # \x91~\x97은 cp1252 따옴표·대시가 latin-1로 잘못 읽힌 경우(1977~2003 HTML 원문)
    s = s.replace("\x93", '"').replace("\x94", '"').replace("\x91", "'").replace("\x92", "'")
    s = s.replace("\x96", "-").replace("\x97", "-")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("–", "-").replace("—", "-").replace("­", "")
    s = re.sub(r"-\s+(?=[a-z])", "-", s)  # PDF 줄바꿈 하이픈
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def load_quotes(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify(quotes, corpus: Path):
    cache, bad = {}, []
    for q in quotes:
        f = corpus / f"{q['year']}.txt"
        if not f.exists():
            bad.append((q["id"], "원문 파일 없음"))
            continue
        text = cache.setdefault(q["year"], norm(f.read_text(encoding="utf-8", errors="ignore")))
        if norm(q["text"]) not in text:
            bad.append((q["id"], "원문에서 찾지 못함"))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "corpus" / "txt"))
    ap.add_argument("--quotes", default=str(ROOT / "persona" / "quotes.jsonl"))
    a = ap.parse_args()
    quotes = load_quotes(Path(a.quotes))
    bad = verify(quotes, Path(a.corpus))
    for qid, why in bad:
        print("FAIL", qid, why)
    print(f"{len(quotes) - len(bad)}/{len(quotes)} 인용이 원문과 일치")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
