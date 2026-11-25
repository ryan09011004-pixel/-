# 워런 버핏 에이전트 (1단계)

버크셔 해서웨이 주주서한(1977~2024)에서 검증한 인용과 알려진 사실, 버핏 스타일 점검표를 바탕으로 버핏의 원칙과 말투를 재현하는 Claude Agent SDK 에이전트입니다. AI 재현이며 버핏 본인의 의견도 투자 조언도 아닙니다.

## 구성
```
persona/
  system_prompt.md   페르소나 정체성, 말투, 인용·사실 규칙, 분석 절차
  quotes.jsonl       원문과 대조해 검증한 인용 29개 (ID, 주제, 연도, 원문 URL, 영어 원문, 한국어 번역)
  facts.md           알려진 사실과 출처 유형, 아직 수집하지 못한 자료
  checklist.yaml     버핏 스타일 점검표 기준값(프로젝트가 정한 기본값)
buffett_agent/
  quotes.py          인용 레지스트리 로드·검색
  checklist.py       점검표 계산(yfinance 값 → 통과·미달·확인 불가)
  tools.py           SDK MCP 도구 3개: search_quotes, get_known_facts, get_buffett_checklist
  agent.py           ClaudeAgentOptions 구성과 질의, CLI
scripts/
  fetch_letters.py   주주서한 원문 내려받기(커밋하지 않음)
  verify_quotes.py   인용이 원문에 글자 그대로 있는지 검증
tests/               오프라인 테스트(원문이 있으면 대조 검증도 실행)
```

## 설치와 실행
```bash
cd agents/buffett
uv venv && uv pip install -e ".[dev]"
python -m buffett_agent "엔비디아를 어떻게 보세요?"
python -m buffett_agent --show-tools "시장이 폭락할 것 같은데 팔아야 할까요?"
```
Claude Agent SDK는 Claude Code의 인증을 그대로 씁니다. 호출마다 비용이 들며, `--show-tools`를 주면 끝에 비용이 출력됩니다.

## 인용 검증
```bash
python scripts/fetch_letters.py     # 원문을 corpus/에 내려받음 (www.berkshirehathaway.com 접근 필요)
python scripts/verify_quotes.py     # 29/29 일치해야 함
pytest -q
```
새 인용을 추가할 때는 `quotes.jsonl`에 한 줄을 넣고 위 검증을 통과시킵니다. 통과하지 못한 문장은 넣지 않습니다.

## 알아둔 사실
- 2025년분 서한은 후임 CEO 그렉 에이블이 쓴 글이라 버핏의 인용 근거에서 제외했습니다.
- 유명한 "훌륭한 기업을 적정한 가격에" 문구는 원문에서 버핏이 찰리 멍거에게 들은 말로 적혀 있습니다(2012 서한 Q12). 의역과 원문이 다릅니다.
- "turnarounds"처럼 원문에 따옴표가 붙은 단어는 그대로 보존했습니다.

## 한계와 다음 단계
- 주총 질의응답 전문, TV 인터뷰, 2025년 11월 서한은 아직 수집하지 못했습니다(해당 사이트가 네트워크 허용 목록에 없음). 확보 전까지 에이전트는 이를 인용하지 않습니다.
- 점검표 기준값은 버핏이 정한 숫자가 아닙니다. 해자, 경영진, 사업 이해 가능성은 숫자로 판정하지 않습니다.
- 최근 행보(애플, 현금, 알파벳)는 2차 보도 기반이라 대략적인 규모로만 씁니다. 정확한 값은 SEC 13F 등 원문으로 확인해야 합니다.
- 해야 할 일: 주총·인터뷰 원문 수집, 주제별 인용 확대, 페르소나 평가 세트(함정 질문 모음) 만들기, 다음 인물로 확장.
