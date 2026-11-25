"""하원 사무처(Clerk) 재산공개 색인에서 특정 의원의 정기 거래 보고서(PTR) 목록을 찾는다."""
from __future__ import annotations

import io
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BASE = "https://disclosures-clerk.house.gov/public_disc/"
UA = {"User-Agent": "pelosi-tracker/0.1 (public STOCK Act disclosures research)"}


@dataclass(frozen=True)
class Filing:
    doc_id: str
    name: str
    filing_type: str  # P = 정기 거래 보고서(PTR), A = 연례 보고서 등
    filing_date: str  # ISO
    year: int
    state_dst: str

    @property
    def pdf_url(self) -> str:
        return f"{BASE}ptr-pdfs/{self.year}/{self.doc_id}.pdf"


def _get(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def fetch_index_xml(year: int, cache: Path | None = None) -> str:
    """해당 연도 색인(YYYYFD.zip)을 받아 XML 문자열을 돌려준다. cache가 있으면 파일로 저장해 재사용."""
    zpath = cache / f"{year}FD.zip" if cache else None
    if zpath and zpath.exists():
        data = zpath.read_bytes()
    else:
        data = _get(f"{BASE}financial-pdfs/{year}FD.zip")
        if zpath:
            zpath.parent.mkdir(parents=True, exist_ok=True)
            zpath.write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read(f"{year}FD.xml").decode("utf-8", errors="ignore")


def parse_index(xml_text: str, last_name: str = "Pelosi", filing_types: tuple[str, ...] = ("P",)) -> list[Filing]:
    out = []
    for m in ET.fromstring(xml_text).iter("Member"):
        g = lambda t: (m.findtext(t) or "").strip()  # noqa: E731
        if g("Last").lower() != last_name.lower() or g("FilingType") not in filing_types:
            continue
        out.append(
            Filing(
                doc_id=g("DocID"),
                name=" ".join(x for x in (g("Prefix"), g("First"), g("Last")) if x),
                filing_type=g("FilingType"),
                filing_date=datetime.strptime(g("FilingDate"), "%m/%d/%Y").strftime("%Y-%m-%d"),
                year=int(g("Year")),
                state_dst=g("StateDst"),
            )
        )
    return sorted(out, key=lambda f: f.filing_date, reverse=True)


def download_pdf(filing: Filing, cache: Path) -> Path:
    path = cache / "ptr" / f"{filing.doc_id}.pdf"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get(filing.pdf_url))
    return path
