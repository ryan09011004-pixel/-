"""버크셔 해서웨이 주주서한(1977~2024)을 내려받아 텍스트로 변환한다.

저작권과 용량 때문에 원문은 저장소에 커밋하지 않는다(`corpus/`는 .gitignore).
인용문 검증(`verify_quotes.py`)과 새 인용 후보 탐색에만 쓴다.

사용: python scripts/fetch_letters.py [--out corpus] [--from 1977] [--to 2024]
필요: pdftotext(poppler-utils), 네트워크에서 www.berkshirehathaway.com 접근 허용
"""
import argparse
import html
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = "https://www.berkshirehathaway.com/letters/"


def letter_name(year: int) -> str:
    # 2003년까지는 HTML, 2004년부터는 PDF
    return f"{year}.html" if year <= 2003 else f"{year}ltr.pdf"


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "buffett-agent-research/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def html_to_text(raw: bytes) -> str:
    s = raw.decode("cp1252", errors="replace")  # 옛 HTML은 cp1252 따옴표를 쓴다
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--from", dest="y0", type=int, default=1977)
    ap.add_argument("--to", dest="y1", type=int, default=2024)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "txt").mkdir(parents=True, exist_ok=True)
    failed = []
    for y in range(a.y0, a.y1 + 1):
        name = letter_name(y)
        raw = out / "raw" / name
        txt = out / "txt" / f"{y}.txt"
        if txt.exists():
            continue
        try:
            fetch(BASE + name, raw)
            if name.endswith(".pdf"):
                subprocess.run(["pdftotext", "-layout", str(raw), str(txt)], check=True)
            else:
                txt.write_text(html_to_text(raw.read_bytes()), encoding="utf-8")
            print("ok", y)
        except Exception as e:  # 네트워크 차단 등은 알려 주고 계속 진행
            failed.append((y, str(e)))
            print("FAIL", y, e, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
