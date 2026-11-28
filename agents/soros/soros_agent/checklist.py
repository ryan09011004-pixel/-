"""소로스 스타일 점검표: 종목(또는 ETF) 하나의 가격이 추세에서 얼마나 멀어졌는지, 붐-버스트 어느 단계 같은지를
계산하고 기준(persona/checklist.yaml)에 대어 본다. 기준값은 프로젝트 기본값이고 단계 판정은 가설이다."""
from __future__ import annotations

import math
import operator
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .quotes import PERSONA_DIR

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}
MIN_DAYS = 253  # 12개월 수익률과 가속도를 계산하려면 약 1년 + 하루
Q = 63  # 한 분기(거래일)


def load_criteria(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or PERSONA_DIR / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["criteria"]


def metrics_from_prices(close: np.ndarray) -> dict[str, Any]:
    """일별 종가(오래된 것부터)에서 점검표 지표를 계산한다. 데이터가 모자라면 해당 지표는 None."""
    c = np.asarray(close, dtype=float)
    c = c[~np.isnan(c)]
    out: dict[str, Any] = {k: None for k in ("ext_vs_200d_pct", "ret_12m_pct", "acceleration_pp", "vol_ratio", "drawdown_from_peak_pct", "downside_asymmetry")}
    out["days"] = int(len(c))
    if len(c) < 30:
        return out
    r = np.diff(c) / c[:-1]
    out["drawdown_from_peak_pct"] = float((c[-1] / c.max() - 1) * 100)
    pos, neg = r[r > 0], r[r < 0]
    if len(pos) and len(neg):
        out["downside_asymmetry"] = float(abs(neg.mean()) / pos.mean())
    if len(r) > Q and r.std(ddof=1) > 0:
        out["vol_ratio"] = float(r[-Q:].std(ddof=1) / r.std(ddof=1))
    if len(c) >= 200:
        out["ext_vs_200d_pct"] = float((c[-1] / c[-200:].mean() - 1) * 100)
    if len(c) >= MIN_DAYS:
        out["ret_12m_pct"] = float((c[-1] / c[-253] - 1) * 100)
        r3 = c[-1] / c[-Q - 1] - 1
        r9 = c[-Q - 1] / c[-253] - 1
        out["acceleration_pp"] = float(r3 * 100 - r9 * 100 / 3)  # 직전 9개월을 분기로 환산해 비교
    return out


def reference_levels(close: np.ndarray) -> dict[str, float | None]:
    """추세가 꺾였는지 보는 참고 기준선. 목표 주가가 아니다."""
    c = np.asarray(close, dtype=float)
    c = c[~np.isnan(c)]
    pick = lambda n: round(float(c[-n:].mean()), 2) if len(c) >= n else None  # noqa: E731
    out = {"last_close": round(float(c[-1]), 2) if len(c) else None, "ma50": pick(50), "ma200": pick(200), "high_3y": round(float(c.max()), 2) if len(c) else None, "low_3y": round(float(c.min()), 2) if len(c) else None}
    last = out["last_close"]
    for k in ("ma50", "ma200", "high_3y", "low_3y"):  # 각 기준선이 현재가보다 몇 % 위(+)/아래(-) — 답변은 이 비율을 쓴다
        out[f"{k}_vs_price_pct"] = round((out[k] / last - 1) * 100, 1) if out[k] and last else None
    return out


def classify_stage(m: dict[str, Any], last_close: float | None = None, ma200: float | None = None) -> dict[str, str]:
    """붐-버스트 단계 가설. 숫자 규칙으로 만든 대략적 분류이며 확정이 아니다."""
    ext, r12, acc = m.get("ext_vs_200d_pct"), m.get("ret_12m_pct"), m.get("acceleration_pp")
    dd, vol = m.get("drawdown_from_peak_pct"), m.get("vol_ratio")
    if ext is None or dd is None:
        return {"stage": "판정 불가", "reason": "데이터가 모자랍니다(200거래일 미만)."}
    if dd <= -20 and ext < 0:
        return {"stage": "붕괴 의심", "reason": "3년 고점 대비 -20% 이상 떨어졌고 200일선 아래입니다."}
    heat = sum(1 for v, th in ((ext, 40), (r12, 100), (acc, 25)) if v is not None and v > th)
    if heat >= 2 and vol is not None and vol > 1.5:
        return {"stage": "황혼 의심", "reason": "과열 신호가 2개 이상인데 최근 변동성도 3년 평균의 1.5배를 넘었습니다."}
    if heat >= 2:
        return {"stage": "가속·과열 의심", "reason": "과열 신호(200일선 이격, 12개월 상승률, 가속)가 2개 이상입니다."}
    if ext > 0 and (r12 is None or r12 > 0):
        return {"stage": "추세 진행", "reason": "200일선 위에 있고 과열 신호는 2개 미만입니다."}
    return {"stage": "추세 약함·판정 불가", "reason": "뚜렷한 상승 추세도 붕괴 신호도 아닙니다."}


def evaluate(metrics: dict[str, Any], criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in criteria:
        value = metrics.get(c["metric"])
        if value is None or (isinstance(value, float) and math.isnan(value)):
            result, value = "확인 불가", None
        else:
            result = "통과" if OPS[c["op"]](value, c["threshold"]) else "미달"
        rows.append({"id": c["id"], "label": c["label"], "value": None if value is None else round(float(value), 2), "rule": f'{c["op"]} {c["threshold"]}', "result": result})
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"통과": 0, "미달": 0, "확인 불가": 0}
    for r in rows:
        out[r["result"]] += 1
    return out
