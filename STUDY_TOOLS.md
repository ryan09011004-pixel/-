# 시험공부 · 문제 만들기 도구 모음

## Claude Code 스킬 (`.claude/skills/`, 이 저장소에서 세션 열면 자동 로드)

| 원본 | 설치된 스킬 | 용도 |
|---|---|---|
| virgiliojr94/book-to-skill | `book-to-skill` | 교재 PDF/EPUB → 학습용 스킬 |
| joeseesun/qiaomu-anything-to-notebooklm | `qiaomu-anything-to-notebooklm` | 여러 자료 → NotebookLM (퀴즈·요약·팟캐스트). `install.sh`로 의존성 설치, NotebookLM 로그인 필요. 유료벽 우회 스크립트(`fetch_url.sh`)는 제외함 |
| bevibing/tutor-skills | `tutor-setup`, `tutor` | 자료 → Obsidian 학습 노트, 퀴즈 |
| LeonChaoX/qinyan-academic-skills (일부) | `literature-review`, `scientific-writing`, `infographics`, `markdown-mermaid-writing`, `scientific-slides`, `scientific-brainstorming`, `scientific-critical-thinking`, `markitdown`, `open-notebook` | 공부·정리에 쓸 만한 9개만 선별 (전체 187개는 연구용이 대부분) |
| ZeKaiNie/universal-examprep-skill (Flash판) | `universal-exam-cram-coach` | 강의자료 근거 시험 대비 코치. PDF용: `pip install pypdfium2` |
| Li-Evan/BloomTutor | `bloom-tutor`, `learn-deep`, `learn-feynman`, `learn-graph`, `learn-occam`, `learn-crossover`, `learn-prototype` | 소크라테스식 튜터, 파인만 학습법 등 |

## 프로그램 (`tools/`, git 서브모듈)

받으려면: `git submodule update --init tools/<이름>`

| 경로 | 용도 |
|---|---|
| `tools/Controllable-RAG-Agent` | 문서 기반 질의응답 RAG 에이전트 (OpenAI 키 필요) |
| `tools/question_generation` | 트랜스포머로 문제 자동 생성 |
| `tools/Questgen.ai` | 객관식/OX/서술형 문제 생성 |
| `tools/AnkiAIUtils` | Anki 카드에 AI 해설·암기법 추가 (AGPL) |
| `tools/deep-student` | 로컬 AI 학습 워크벤치 데스크톱 앱 (AGPL, 약 300MB) |
