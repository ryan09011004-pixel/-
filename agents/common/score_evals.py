"""평가 세트(evals/trap_questions.jsonl)를 '이미 받은 답변'으로 채점한다. 이 스크립트는 모델을 호출하지 않는다.

사용:
  python common/score_evals.py <agent> answers.jsonl      # answers.jsonl: {"id": "T01", "answer": "..."} 한 줄씩
  python common/score_evals.py --list <agent>             # 질문 목록
각 질문은 형식 검사(format_check) + must_include / must_not_include 문자열 규칙으로 통과·실패를 정한다.
의미 판단이 필요한 `expect`는 사람이 읽고 확인해야 하며 이 점수에 들어가지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.format_check import ROOT, check_answer  # noqa: E402


def load_evals(agent: str) -> list[dict]:
    path = ROOT / agent / "evals" / "trap_questions.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def score(agent: str, answers: dict[str, str]) -> list[dict]:
    rows = []
    for q in load_evals(agent):
        ans = answers.get(q["id"])
        if ans is None:
            rows.append({"id": q["id"], "kind": q["kind"], "result": "답변 없음", "problems": []})
            continue
        problems = check_answer(agent, ans, 1 if q["kind"] == "out_of_scope" else 3)
        problems += [f"필수 문구 없음: {s}" for s in q.get("must_include", []) if s not in ans]
        problems += [f"금지 문구 포함: {s}" for s in q.get("must_not_include", []) if s in ans]
        rows.append({"id": q["id"], "kind": q["kind"], "result": "통과" if not problems else "실패", "problems": problems})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", choices=sorted(__import__("common.format_check", fromlist=["HEADERS"]).HEADERS))
    ap.add_argument("answers", nargs="?")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.answers:
        for q in load_evals(a.agent):
            print(f'{q["id"]} [{q["kind"]}] {q["question"]}')
        return 0
    answers = {}
    for l in Path(a.answers).read_text(encoding="utf-8").splitlines():
        if l.strip():
            row = json.loads(l)
            answers[row["id"]] = row["answer"]
    rows = score(a.agent, answers)
    for r in rows:
        print(r["id"], r["kind"], r["result"], "; ".join(r["problems"]))
    ok = sum(r["result"] == "통과" for r in rows)
    print(f"{ok}/{len(rows)} 통과")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
