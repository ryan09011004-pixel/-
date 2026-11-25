import json
from pathlib import Path

import pytest

from pelosi_tracker import analyze, cli, index, ptr

FX = Path(__file__).parent / "fixtures"
COUNTS = {"20033725": 18, "20034836": 2, "20035143": 7, "20035553": 1, "20035780": 1}  # 원문 거래 줄 수와 일치해야 한다


def load(doc_id):
    return ptr.parse_ptr_text((FX / f"{doc_id}.txt").read_text(encoding="utf-8"), doc_id)


@pytest.mark.parametrize("doc_id,n", COUNTS.items())
def test_parser_finds_every_transaction_row(doc_id, n):
    assert len(load(doc_id)) == n


def test_single_trade_fields_are_normalized():
    (t,) = load("20035780")
    assert (t.owner, t.ticker, t.asset_code, t.txn_type) == ("SP", "WBD", "ST", "S")
    assert (t.txn_date, t.notified_date, t.amount_low, t.amount_high) == ("2026-10-07", "2026-10-07", 50001, 100000)
    assert "Paramount" in t.description and t.as_dict()["owner_ko"] == "배우자" and t.as_dict()["type_ko"] == "매도"


def test_rows_with_tight_columns_and_decimals_are_not_dropped():
    trades = load("20033725")
    nv = [t for t in trades if t.ticker == "NVDA"]
    assert len(nv) == 3 and {t.asset_code for t in nv} == {"OP", "ST"}  # 자산명과 유형 사이가 한 칸뿐인 행
    vs = next(t for t in trades if t.ticker == "VSNT")
    assert (vs.txn_type, vs.amount_low, vs.amount_high) == ("E", 15, None)  # '$15.00' 현금 정산, 구간이 아님


def test_option_rows_and_private_assets():
    trades = [t for doc_id in COUNTS for t in load(doc_id)]
    assert any(t.asset_code == "OP" for t in trades)
    assert any(t.ticker is None for t in trades)  # 비상장 펀드(REOF 등)는 티커가 없다
    assert all(t.amount_low is not None for t in trades)


def test_negative_amounts_are_formatted_with_sign_first():
    assert cli._fmt_range(-5_000_000, -1_000_001) == "-$5,000,000~-$1,000,001"
    assert cli._fmt_range(15, None) == "$15" and cli._fmt_range(None, None) == "?"


def test_net_range_is_a_range_not_a_point():
    rows = analyze.net_by_ticker(load("20033725"))
    nv = next(r for r in rows if r["key"] == "NVDA")
    assert nv["buys"] == 2 and nv["sells"] == 1
    lo, hi = nv["net_range"]
    assert lo == nv["buy_range"][0] - nv["sell_range"][1] and hi == nv["buy_range"][1] - nv["sell_range"][0] and lo < hi


def test_delay_days_against_45_day_rule():
    (t,) = load("20035780")
    assert analyze.delay_days(t, "2026-11-06") == 30


XML = """<FinancialDisclosure>
<Member><Prefix>Hon.</Prefix><Last>Pelosi</Last><First>Nancy</First><FilingType>P</FilingType><StateDst>CA11</StateDst><Year>2026</Year><FilingDate>11/6/2026</FilingDate><DocID>20035780</DocID></Member>
<Member><Prefix>Hon.</Prefix><Last>Pelosi</Last><First>Nancy</First><FilingType>A</FilingType><StateDst>CA11</StateDst><Year>2026</Year><FilingDate>5/15/2026</FilingDate><DocID>10000001</DocID></Member>
<Member><Prefix>Hon.</Prefix><Last>Other</Last><First>Pat</First><FilingType>P</FilingType><StateDst>TX01</StateDst><Year>2026</Year><FilingDate>11/9/2026</FilingDate><DocID>20035999</DocID></Member>
<Member><Prefix>Hon.</Prefix><Last>Pelosi</Last><First>Nancy</First><FilingType>P</FilingType><StateDst>CA11</StateDst><Year>2026</Year><FilingDate>1/23/2026</FilingDate><DocID>20033725</DocID></Member>
</FinancialDisclosure>"""


def test_index_filters_member_and_filing_type_and_sorts_newest_first():
    fs = index.parse_index(XML, "pelosi")
    assert [f.doc_id for f in fs] == ["20035780", "20033725"]  # 연례 보고서(A)와 다른 의원은 제외
    assert fs[0].filing_date == "2026-11-06" and fs[0].pdf_url.endswith("/ptr-pdfs/2026/20035780.pdf")


def test_cli_parse_prints_trades_and_disclaimer(capsys):
    assert cli.main(["parse", str(FX / "20035780.txt")]) == 0
    out = capsys.readouterr().out
    assert "WBD" in out and "배우자" in out and "투자 조언이 아닙니다" in out


def test_cli_parse_json_is_valid(capsys):
    assert cli.main(["parse", str(FX / "20035143.txt"), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 7 and {"ticker", "amount_low", "owner_ko", "delay_days"} <= set(rows[0])
