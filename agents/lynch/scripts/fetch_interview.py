"""린치의 1996년 PBS FRONTLINE 인터뷰 페이지를 받아 corpus/txt/frontline-1996.txt로 저장한다.

저작권(WGBH) 때문에 원문은 커밋하지 않는다(corpus/는 .gitignore). 인용 검증(verify_quotes.py)에만 쓴다.
사용: python scripts/fetch_interview.py   (www.pbs.org 접근 필요)
"""
import html
import re
import urllib.request
from pathlib import Path

URL = "https://www.pbs.org/wgbh/pages/frontline/shows/betting/pros/lynch.html"
OUT = Path(__file__).resolve().parents[1] / "corpus" / "txt" / "frontline-1996.txt"


def main() -> None:
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "lynch-agent-research/0.1"}), timeout=60).read()
    s = raw.decode("utf-8", errors="replace")
    s = re.sub(r"(?is)<(script|style|nav|header|footer).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    i = s.index("How did you first get interested")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(re.sub(r"\s*\n\s*", " ", s[i:]), encoding="utf-8")
    print("saved", OUT)


if __name__ == "__main__":
    main()
