"""하원 정기 거래 보고서(PTR) PDF 텍스트를 거래 목록으로 파싱한다.

입력은 `pdftotext -layout` 결과다. 공시 한 건의 거래 한 줄은 대략 이렇게 보인다.

    SP   Alphabet Inc. - Class A Common    P    01/16/2026 01/16/2026   $500,001 -
         Stock (GOOGL) [ST]                                              $1,000,000
         F  S : New
         D    : Exercised 50 call options ...
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

ROW = re.compile(
    r"^\s*(?:(?P<owner>SP|JT|DC)\s{2,})?(?P<asset>\S.*?)\s+"
    r"(?P<type>S \(partial\)|P|S|E)\s+(?P<tdate>\d{2}/\d{2}/\d{4})\s+(?P<ndate>\d{2}/\d{2}/\d{4})\s+(?P<amt>\$[\d,]+.*)?$"
)
SKIP = re.compile(r"^\s*(ID\s+Owner\s+Asset|Type\s+Date\s+Date|Gains\s*>|\$200\?|Filing ID #|F\s+S\s+:|T\s*$|P\s+T\s+R)")
END = re.compile(r"^\s*(\*|I\s+P\s+O|C\s+S\s*$|Digitally Signed|I CERTIFY)")
DESC = re.compile(r"^\s*D\s+:\s*(?P<d>.*)$")
OWNERS = {"SP": "배우자", "JT": "공동", "DC": "자녀", "본인": "본인"}
TYPES = {"P": "매수", "S": "매도", "S (partial)": "일부 매도", "E": "교환"}


@dataclass
class Trade:
    filing_id: str
    owner: str
    asset: str
    ticker: str | None
    asset_code: str | None
    txn_type: str
    txn_date: str
    notified_date: str
    amount_low: int | None
    amount_high: int | None
    description: str = ""
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["owner_ko"] = OWNERS.get(self.owner, self.owner)
        d["type_ko"] = TYPES.get(self.txn_type, self.txn_type)
        return d


def _iso(mdy: str) -> str:
    return datetime.strptime(mdy, "%m/%d/%Y").strftime("%Y-%m-%d")


def _money(s: str) -> int:
    return round(float(s.replace("$", "").replace(",", "")))  # 현금 정산 같은 '$15.00'도 처리


def _amounts(text: str) -> tuple[int | None, int | None]:
    vals = [_money(m) for m in re.findall(r"\$[\d,]+(?:\.\d+)?", text)]
    if not vals:
        return None, None
    return vals[0], (vals[1] if len(vals) > 1 else None)


def parse_ptr_text(text: str, filing_id: str = "") -> list[Trade]:
    """PTR 텍스트에서 거래를 뽑는다. 거래 표가 없으면 빈 목록."""
    if not filing_id:
        m = re.search(r"Filing ID #(\d+)", text)
        filing_id = m.group(1) if m else ""
    blocks: list[dict] = []
    cur: dict | None = None
    in_desc = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if END.match(line):
            cur, in_desc = None, False
            continue
        m = ROW.match(line)
        if m:
            cur = {"m": m, "asset_lines": [m.group("asset").strip()], "amt_lines": [m.group("amt") or ""], "desc": [], "n": 0}
            blocks.append(cur)
            in_desc = False
            continue
        if cur is None or SKIP.match(line) or not line.strip():
            if not line.strip():
                in_desc = False
            continue
        d = DESC.match(line)
        if d:
            cur["desc"].append(d.group("d").strip())
            in_desc = True
        elif in_desc:
            cur["desc"].append(line.strip())
        elif cur["n"] < 2:  # 자산명 둘째 줄과 금액 둘째 줄
            cur["n"] += 1
            amt = re.search(r"\$[\d,]+(?:\.\d+)?\s*$", line)
            body = line[: amt.start()] if amt else line
            if body.strip():
                cur["asset_lines"].append(body.strip())
            if amt:
                cur["amt_lines"].append(amt.group(0).strip())
    trades = []
    for b in blocks:
        m = b["m"]
        asset = " ".join(b["asset_lines"])
        tk = re.search(r"\(([A-Z][A-Z0-9.\-]{0,6})\)", asset)
        code = re.search(r"\[([A-Z]{2})\]", asset)
        low, high = _amounts(" ".join(b["amt_lines"]))
        trades.append(
            Trade(
                filing_id=filing_id,
                owner=m.group("owner") or "본인",
                asset=re.sub(r"\s*\[[A-Z]{2}\]\s*$", "", asset).strip(),
                ticker=tk.group(1) if tk else None,
                asset_code=code.group(1) if code else None,
                txn_type=m.group("type"),
                txn_date=_iso(m.group("tdate")),
                notified_date=_iso(m.group("ndate")),
                amount_low=low,
                amount_high=high,
                description=" ".join(b["desc"]).strip(),
            )
        )
    return trades


def pdf_to_text(pdf: Path) -> str:
    try:
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    except FileNotFoundError as e:
        raise RuntimeError("pdftotext가 필요합니다(poppler-utils).") from e
