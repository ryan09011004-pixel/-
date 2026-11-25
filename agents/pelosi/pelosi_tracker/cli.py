"""명령줄: 최근 공시 보기(recent), 종목별 집계(summary), 로컬 파일 파싱(parse). 모델 호출·유료 API 없음."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import analyze, index, ptr

DISCLAIMER = (
    "※ 하원 STOCK Act 공시(공개 자료)를 정리한 것입니다. 거래의 상당수는 배우자 명의이고, 금액은 구간으로만 공개되며, "
    "공시는 거래 후 최대 45일 늦게 나옵니다. 이 자료는 위법이나 내부정보 이용의 근거가 아니며 투자 조언이 아닙니다."
)


def _usd(n: int) -> str:
    return f"-${-n:,}" if n < 0 else f"${n:,}"


def _fmt_range(lo, hi) -> str:
    if lo is None:
        return "?"
    return _usd(lo) if hi is None or hi == lo else f"{_usd(lo)}~{_usd(hi)}"


def load_trades(name: str, year: int, days: int, cache: Path, today: date | None = None) -> list[tuple[ptr.Trade, str]]:
    today = today or date.today()
    since = (today - timedelta(days=days)).isoformat()
    filings = [f for f in index.parse_index(index.fetch_index_xml(year, cache), name) if f.filing_date >= since]
    out = []
    for f in filings:
        text = ptr.pdf_to_text(index.download_pdf(f, cache))
        out.extend((t, f.filing_date) for t in ptr.parse_ptr_text(text, f.doc_id))
    return sorted(out, key=lambda x: x[0].txn_date, reverse=True)


def print_trades(pairs: list[tuple[ptr.Trade, str]], as_json: bool) -> None:
    if as_json:
        print(json.dumps([dict(t.as_dict(), filing_date=fd, delay_days=analyze.delay_days(t, fd)) for t, fd in pairs], ensure_ascii=False, indent=2))
        return
    for t, fd in pairs:
        tk = t.ticker or t.asset[:24]
        code = f"[{t.asset_code}]" if t.asset_code else ""
        print(f"{t.txn_date}  {t.as_dict()['type_ko']:<5} {tk:<8}{code:<5} {_fmt_range(t.amount_low, t.amount_high):<24} {t.as_dict()['owner_ko']:<3} (공시 {fd}, {analyze.delay_days(t, fd)}일 지연)")
        if t.description:
            print(f"            └ {t.description[:110]}")
    print(f"\n{DISCLAIMER}")


def print_summary(trades: list[ptr.Trade], as_json: bool) -> None:
    rows = analyze.net_by_ticker(trades)
    if as_json:
        print(json.dumps({"summary": analyze.summarize(trades), "by_ticker": rows}, ensure_ascii=False, indent=2, default=list))
        return
    s = analyze.summarize(trades)
    print(f"거래 {s['trades']}건(매수 {s['buys']}, 매도 {s['sells']}, 옵션 {s['options']}), 종목 {s['tickers']}개, 소유자 {', '.join(s['owners'])}")
    for r in rows:
        print(f"{r['key']:<10} 매수 {r['buys']}건 {_fmt_range(*r['buy_range'])} / 매도 {r['sells']}건 {_fmt_range(*r['sell_range'])} / 순매수 {_fmt_range(*r['net_range'])}")
    print(f"\n{DISCLAIMER}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pelosi_tracker", description="하원 의원 공시 거래 추적(공개 자료, 비용 없음)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("recent", "summary"):
        p = sub.add_parser(name)
        p.add_argument("--name", default="Pelosi", help="의원 성(영문)")
        p.add_argument("--year", type=int, default=date.today().year)
        p.add_argument("--days", type=int, default=90, help="최근 N일에 제출된 공시")
        p.add_argument("--cache", default=str(Path.home() / ".cache" / "pelosi_tracker"))
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("parse", help="내려받은 PTR PDF 또는 텍스트 파일을 파싱")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "parse":
            path = Path(a.file)
            text = ptr.pdf_to_text(path) if path.suffix.lower() == ".pdf" else path.read_text(encoding="utf-8")
            trades = ptr.parse_ptr_text(text)
            print_trades([(t, t.notified_date) for t in trades], a.json)
        else:
            pairs = load_trades(a.name, a.year, a.days, Path(a.cache))
            (print_trades(pairs, a.json) if a.cmd == "recent" else print_summary([t for t, _ in pairs], a.json))
    except Exception as e:  # 네트워크 차단·형식 변경은 숨기지 않고 알린다
        print(f"실패: {e}", file=sys.stderr)
        return 1
    return 0
