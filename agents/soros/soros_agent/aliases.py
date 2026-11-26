"""질문 확장: 한국어 종목·주제 말을 사례·인용 검색용 키워드로 넓힌다(모델 호출 없음).

다섯 에이전트 패키지가 각자 같은 복사본(`<agent>_agent/aliases.py`)을 가진다. 원본은 이 파일이고,
common/tests가 복사본이 같은지 확인한다. 사전에 없는 말(예: 비트코인)은 넓히지 않아 '관련 사례 없음'이 그대로 나온다.
"""
from __future__ import annotations

import re

# (질문에 이 정규식이 있으면, 아래 키워드를 검색어에 덧붙인다)
ALIASES: list[tuple[str, str]] = [
    (r"엔비디아|nvda|nvidia|반도체|(?<![a-z])ai(?![a-z])|인공지능|테슬라|tsla|애플|aapl|마이크로소프트|msft|구글|알파벳|메타|테크|기술주|빅테크", "기술 tech technology 능력의원 circle_of_competence 빠르게변하는 성장 growth 모멘텀 버블"),
    (r"코카콜라|(?<![a-z])ko(?![a-z])|펩시|맥도날드|브랜드|소비재", "코카콜라 브랜드 brand 해자 moat 소비자 소비재 장기 long_term"),
    (r"버블|거품|과열", "버블 거품 bubble boom bust 붐 과열 공포 탐욕 fear_greed"),
    (r"폭락|위기|공황|패닉|금융위기", "위기 crisis crash 공포 fear 폭락 현금 cash 금융위기 시장 market"),
    (r"금리|채권|국채|인플레|물가|(?<![a-z])tlt(?![a-z])", "금리 채권 bond 인플레이션 inflation 물가 금리 interest 부채 debt"),
    (r"금값|골드|(?<![a-z])gld(?![a-z])|(?<![가-힣])금(?:을|은|이|가|값)?(?![가-힣])", "금 gold 안전자산 inflation 물가대비"),
    (r"부동산|집값|주택|대출|담보", "부동산 real estate 대출 신용 credit 담보 collateral 주택"),
    (r"환율|달러|외환|원화|통화", "환율 통화 currency exchange 달러 파동"),
    (r"은행|보험|금융주", "은행 bank 보험 insurance 금융 financial"),
    (r"자사주|배당|buyback|dividend", "자사주 buyback 배당 dividend 주주환원 가격 price"),
    (r"인덱스|etf|펀드|수수료", "인덱스펀드 index_fund 수수료 fees etf 분산 diversification"),
    (r"분산|포트폴리오|리스크|위험", "분산 diversification 포트폴리오 portfolio 위험 risk 균형 balance"),
    (r"저평가|싸다|가치투자|안전마진|(?<![a-z])pbr(?![a-z])|(?<![a-z])per(?![a-z])", "저평가 안전마진 margin_of_safety 가치 value 가격 price pbr per"),
    (r"파산|부채|빚|적자", "부채 debt 파산 bankruptcy 재무 안전 balance_sheet"),
    (r"적자 기업|턴어라운드|회생", "회생 turnaround 구조조정"),
]
# 질문에 흔히 섞이지만 검색 의미가 없는 말(부분 문자열로 엉뚱한 사례에 걸리는 것을 막는다)
STOPWORDS = {"지금", "하나", "어떻게", "생각해", "생각은", "사야", "팔아야", "해야", "있나", "어때", "어떤", "이게", "뭐예요", "알려", "주세요", "정말"}
_COMPILED = [(re.compile(p, re.I), extra) for p, extra in ALIASES]


def expand(query: str) -> str:
    """질문 뒤에 사전에서 찾은 검색 키워드를 붙여 돌려준다. 해당 없으면 질문 그대로."""
    q = query.strip()
    extras = [extra for rx, extra in _COMPILED if rx.search(q)]
    return q if not extras else q + " " + " ".join(extras)
