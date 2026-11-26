"""조지 소로스 본인이 공개한 두 원문을 내려받아 corpus/txt/에 저장한다(무료, 키 없음).

- soros-essay-2014: georgesoros.com의 「Fallibility, Reflexivity, and the Human Uncertainty Principle」(2013, Journal of Economic Methodology 기고)
- soros-lecture-2009: Open Society Foundations의 「General Theory of Reflexivity」 강연 녹취(2009-10-26, 중앙유럽대학교)

저작권 때문에 원문은 커밋하지 않는다(corpus/는 .gitignore). 인용·사례 증거 검증(verify_quotes.py)에만 쓴다.
사용: python scripts/fetch_sources.py   (georgesoros.com, opensocietyfoundations.org 접근 필요, pdftotext 필요)
"""
import html
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ESSAY_URL = "https://www.georgesoros.com/2014/01/13/fallibility-reflexivity-and-the-human-uncertainty-principle-2/"
LECTURE_URL = "https://www.opensocietyfoundations.org/uploads/9ae17912-2262-4646-8ffc-d01afc934c36/george-soros-general-theory-of-reflexivity-transcript.pdf"
OUT = Path(__file__).resolve().parents[1] / "corpus" / "txt"
UA = {"User-Agent": "soros-agent-research/0.1"}


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def clean(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|figure|iframe|nav|footer|header).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</blockquote>", "\n", h)
    h = html.unescape(re.sub(r"<[^>]+>", "", h))
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", h)).strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page = get(ESSAY_URL).decode("utf-8", errors="ignore")
    m = re.search(r'(?is)<div[^>]+class="[^"]*entry-content[^"]*"[^>]*>(.*)', page)
    (OUT / "soros-essay-2014.txt").write_text(clean(m.group(1) if m else page), encoding="utf-8")
    print("saved soros-essay-2014")
    with tempfile.TemporaryDirectory() as d:
        pdf = Path(d) / "lecture.pdf"
        pdf.write_bytes(get(LECTURE_URL))
        subprocess.run(["pdftotext", "-layout", str(pdf), str(OUT / "soros-lecture-2009.txt")], check=True)
    print("saved soros-lecture-2009")


if __name__ == "__main__":
    main()
