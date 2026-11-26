"""레이 달리오의 서브스택 'Principled Perspectives' RSS(최근 글 전문)를 받아 corpus/txt/에 글별 텍스트로 저장한다.

저작권(달리오) 때문에 원문은 커밋하지 않는다(corpus/는 .gitignore). 인용·사례 증거 검증(verify_quotes.py)에만 쓴다.
사용: python scripts/fetch_posts.py   (raydalio.substack.com 접근 필요, 무료)
"""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED = "https://raydalio.substack.com/feed"
OUT = Path(__file__).resolve().parents[1] / "corpus" / "txt"
NS = {"c": "http://purl.org/rss/1.0/modules/content/"}


def clean(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|figure|iframe).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</blockquote>", "\n", h)
    h = html.unescape(re.sub(r"<[^>]+>", "", h))
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", h)).strip()


def main() -> None:
    raw = urllib.request.urlopen(urllib.request.Request(FEED, headers={"User-Agent": "dalio-agent-research/0.1"}), timeout=60).read()
    OUT.mkdir(parents=True, exist_ok=True)
    for it in ET.fromstring(raw).findall("./channel/item"):
        title, link = it.findtext("title"), it.findtext("link")
        day = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")
        body = clean(it.findtext("c:encoded", namespaces=NS) or it.findtext("description") or "")
        slug = link.rstrip("/").split("/")[-1][:40]
        (OUT / f"{day}-{slug}.txt").write_text(f"{title}\n{link}\n\n{body}", encoding="utf-8")
        print("saved", day, slug)


if __name__ == "__main__":
    main()
