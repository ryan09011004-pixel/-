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
        doc = q.get("doc") or str(q["year"])  # 주주서한은 연도, 보도자료는 doc 이름(news-YYYY-MM-DD)
        f = corpus / f"{doc}.txt"
        if not f.exists():
            bad.append((q["id"], "원문 파일 없음"))
            continue
        text = cache.setdefault(doc, norm(f.read_text(encoding="utf-8", errors="ignore")))
        if norm(q["text"]) not in text:
            bad.append((q["id"], "원문에서 찾지 못함"))
    return bad


def verify_cases(cases, corpus: Path):
    """사례집(cases.jsonl)의 증거 문장이 해당 연도 서한 원문에 그대로 있는지 확인한다."""
    rows = []
    for c in cases:
        for i, ev in enumerate(c.get("evidence", []), 1):
            rows.append({"id": f"{c['id']}#{i}", "year": ev["year"], "text": ev["text"], "doc": ev.get("doc", "")})
    return len(rows), verify(rows, corpus)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "corpus" / "txt"))
    ap.add_argument("--quotes", default=str(ROOT / "persona" / "quotes.jsonl"))
    ap.add_argument("--cases", default=str(ROOT / "persona" / "cases.jsonl"))
    a = ap.parse_args()
    quotes = load_quotes(Path(a.quotes))
    bad = verify(quotes, Path(a.corpus))
    for qid, why in bad:
        print("FAIL", qid, why)
    print(f"{len(quotes) - len(bad)}/{len(quotes)} 인용이 원문과 일치")
    failed = bool(bad)
    cases_path = Path(a.cases)
    if cases_path.exists():
        cases = load_quotes(cases_path)  # 같은 jsonl 형식
        total, cbad = verify_cases(cases, Path(a.corpus))
        for cid, why in cbad:
            print("FAIL", cid, why)
        print(f"{total - len(cbad)}/{total} 사례 증거가 원문과 일치")
        failed = failed or bool(cbad)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
