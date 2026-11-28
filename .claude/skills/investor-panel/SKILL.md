---
name: investor-panel
description: 투자 대가 5인(워런 버핏, 벤저민 그레이엄, 피터 린치, 레이 달리오, 조지 소로스) AI 재현 패널. 사용자가 "버핏이라면?", "소로스는 NVDA 어떻게 봐?", "5명 의견", "/investor-panel 티커" 처럼 투자 대가의 관점을 물을 때 쓴다. 이 저장소 agents/의 검증된 인용·사례·점검표만 근거로, 승인된 3줄 형식으로 답한다. 별도 모델·API 호출이 없어 추가 비용이 없다.
---

# 투자 대가 패널

## 원칙 (반드시 지킴)
- **추가 비용 금지**: `python -m <agent>_agent`(Agent SDK 호출)나 유료 API를 쓰지 않는다. 근거는 `agents/panel.py`(무료 로컬 도구 + Yahoo Finance + 공개 CSV)로만 모으고, 답은 지금 대화 중인 Claude가 쓴다.
- 각 에이전트의 `agents/<agent>/persona/system_prompt.md`를 먼저 읽고 그 규칙을 그대로 따른다(인용은 ID 있는 것만, 예측·지시·목표가 금지, 가격 대신 현재가 대비 비율).
- 시장 배경(`--market`)은 점수·구간만 쓴다. 스킬의 매매 행동 지침은 이미 제거돼 있으며 다시 만들어 내지 않는다.

## 순서
1. 질문에서 에이전트(하나 또는 `all`)와 티커를 정한다. 티커가 없으면 `--ticker`를 빼고, 시장 전체 질문이면 `--market`을 붙인다. 달리오는 티커 하나 또는 `SPY:60,TLT:40` 형식 포트폴리오를 받는다.
2. 근거 모으기:
   ```bash
   python agents/panel.py evidence <agent|all> "<질문>" --ticker <TICKER> --market
   ```
   필요한 패키지가 없으면 `pip install yfinance pyyaml numpy`(무료) 후 다시 실행한다.
3. 에이전트마다 system_prompt의 3줄 형식으로 답을 쓴다: 첫 줄 머리글(`header` 값 그대로), 이어서 의견 / 들어갈 때 / 멈출 때 3줄, 각 줄 `(추정)`, ID는 괄호 안에만, 숫자는 근거 JSON에 있는 값만(가격 금액 대신 `..._vs_price_pct` 비율).
4. 답마다 형식 검사:
   ```bash
   python agents/panel.py check <agent> answer.txt      # 범위 밖 거절은 --one-line
   ```
   "형식 통과"가 아니면 지적된 부분만 고쳐 한 번 더 검사한다.
5. 사용자에게는 통과한 답만 보여 준다. 여러 명이면 에이전트 순서대로 블록을 나란히 둔다. 과정 설명은 하지 않는다(사용자 선호).

## 여러 명 비교가 필요할 때
`python agents/compare.py <TICKER>`로 다섯 점검표 표를 먼저 만들고, 그 표를 한 줄로 요약한 뒤 각자의 3줄을 붙인다.

## 채점(선택)
사용자가 원하면 답을 `answers.jsonl`({"id","answer"})로 모아 `python agents/common/judge.py packet <agent> answers.jsonl`로 GPT 붙여넣기 묶음을 만들고, 돌려받은 결과를 `merge`로 합친다(API 호출 없음).
