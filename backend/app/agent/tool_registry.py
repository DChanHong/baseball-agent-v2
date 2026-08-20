from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from app.agent.routing_schemas import (
    FindKboGameRoutingArgs,
    GetStadiumInfoRoutingArgs,
    GetWeatherContextRoutingArgs,
    SearchBaseballKnowledgeRoutingArgs,
    SearchStadiumGuideRoutingArgs,
    SearchTicketingGuideRoutingArgs,
)
from app.domains.baseball.tool.find_kbo_game.schemas import FindKboGameToolInput
from app.domains.baseball.tool.get_stadium_info.schemas import GetStadiumInfoToolInput
from app.domains.baseball.tool.get_weather_context.schemas import (
    GetWeatherContextToolInput,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    SearchBaseballKnowledgeToolInput,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
)
from app.domains.baseball.tool.search_ticketing_guide.schemas import (
    SearchTicketingGuideToolInput,
)

ToolName = str


@dataclass(frozen=True)
class AgentToolSpec:
    name: ToolName
    routing_args_type: type[BaseModel]
    tool_input_type: type[BaseModel]
    executor_handler_attr: str
    display_label: str
    routing_card: str


FIND_KBO_GAME_TOOL_CARD = """
도구명: find_kbo_game

역할:
- KBO 경기 일정, 경기 유무, 경기 장소, 경기 상태, 취소 사유, 점수를 정형 DB에서 조회한다.

입력:
- team_id: KBO 팀 ID 또는 null
- date: 단일 조회 날짜. date_from/date_to와 함께 쓰지 않는다.
- date_from: 기간 조회 시작일
- date_to: 기간 조회 종료일

호출해야 하는 경우:
- "오늘 롯데 경기 있어?"
- "롯데 7월 일정 알려줘"
- "7월 17일 롯데 경기 왜 취소됐어?"
- "LG 개막전 어디서 해?"
- "내일 고척 경기 있어?"

호출하지 않는 경우:
- 일반 야구 규칙, 플레이 설명, 최신 KBO 규정 질문
- 팀 역사, 응원 문화, 구장 준비물, 직관 팁 질문
- 현재 티켓 잔여 여부
- 날씨 또는 미래/실시간 우천 취소 예측
- 두 팀 간 맞대결 일정 필터

미지원 분류:
- 티켓 잔여 여부: ticket_inventory_tool_required
- 날씨 또는 미래/실시간 우천 취소 예측: weather_or_realtime_cancellation_prediction_required
- 두 팀 간 맞대결 일정: opponent_team_filter_not_supported_yet
""".strip()


SEARCH_BASEBALL_KNOWLEDGE_TOOL_CARD = """
도구명: search_baseball_knowledge

역할:
- 공식야구규칙, KBO 리그 규정, 자주 나오는 플레이/판정 설명을 RAG 문서에서 검색한다.
- 검색 결과는 답변 생성에 사용할 근거 chunk, 출처 URL, 기준 시점, 신뢰 등급을 포함한다.

입력:
- query: 사용자의 원문 질문
- knowledge_types: 좁힐 수 있으면 문서 유형 목록, 넓은 질문이면 null
- top_k: 기본 5

knowledge_types:
- baseball_rule: 야구 기본 규칙, 득점, 볼/스트라이크, 페어/파울, 아웃, 주자 진루, 정식경기
- common_play: 보크, 인필드 플라이, 태그아웃/포스아웃, 도루/견제, 희생플라이, 병살, 폭투/포일
- latest_kbo_rule: 비디오 판독, 체크스윙 판독, ABS, 피치클락, 우천취소/노게임/서스펜디드, 경기 거행 권한

호출해야 하는 경우:
- "야구는 어떻게 이기는 거야?"
- "볼이랑 스트라이크가 뭐야?"
- "인필드 플라이가 왜 선언돼?"
- "보크가 뭐야?"
- "피치클락 위반하면 어떻게 돼?"
- "비 오면 누가 경기 취소를 결정해?"
- "노게임이랑 서스펜디드는 뭐가 달라?"

호출하지 않는 경우:
- 특정 날짜 경기 일정, 경기 유무, 경기 상태 질문은 find_kbo_game을 사용한다.
- 구장 주소, 돔 여부, 홈팀, 지역, 기본 식별 정보 질문은 get_stadium_info를 사용한다.
- 구장별 예매, 좌석, 반입 정책, 교통, 주차, 편의시설 질문은 search_stadium_guide를 사용한다.
- 선수/팀 역사, 실시간 티켓 잔여석, 실시간 주차 가능 대수는 현재 지원하지 않는다.
- "오늘 경기 우천 취소될까?"처럼 특정 경기의 미래/실시간 취소 예측은 확정 답변하지 않는다.
""".strip()


GET_STADIUM_INFO_TOOL_CARD = """
도구명: get_stadium_info

역할:
- KBO 구장의 정형 기본 정보를 DB에서 조회한다.
- 구장명, 짧은 이름, 별칭, 도시/지역, 주소, 돔 여부, 홈팀, 공식/출처 URL, 기준 시점을 반환한다.

입력:
- stadium_id: KBO 구장 ID. 구장을 직접 알 수 있으면 사용한다.
- team_id: KBO 팀 ID. "롯데 홈구장", "우리 팀 홈구장"처럼 팀 기준이면 사용한다.

호출해야 하는 경우:
- "사직구장 주소 알려줘"
- "고척돔은 돔구장이야?"
- "롯데 홈구장 어디야?"
- "잠실야구장은 어느 팀 홈구장이야?"
- "문학구장 기본 정보 알려줘"

호출하지 않는 경우:
- 경기 일정, 경기 유무, 경기 상태 질문은 find_kbo_game을 사용한다.
- 예매 방법, 좌석 종류, 반입 정책, 교통/주차 세부 안내, 편의시설 설명은 search_stadium_guide를 사용한다.
- 야구 규칙, 플레이 설명, 최신 KBO 규정 질문은 search_baseball_knowledge를 사용한다.
""".strip()


SEARCH_STADIUM_GUIDE_TOOL_CARD = """
도구명: search_stadium_guide

역할:
- KBO 홈구장의 좌석, 반입 정책, 교통, 주차, 편의시설 안내를 RAG 문서에서 검색한다.
- 검색 결과는 답변 생성에 사용할 근거 chunk, 출처 URL, 기준 시점, 신뢰 등급을 포함한다.

입력:
- stadium_id: 필수 KBO 구장 ID
- team_id: 팀 맥락이 있으면 KBO 팀 ID, 없으면 null
- query: 사용자의 원문 질문
- guide_types: 좁힐 수 있으면 문서 유형 목록, 넓은 질문이면 null
- top_k: 기본 5

구장 ID:
- SAJIK: 사직야구장, 롯데 홈구장
- GOCHEOK: 고척스카이돔, 키움 홈구장
- MUNHAK: 인천 SSG 랜더스필드, 문학구장, SSG 홈구장
- GWANGJU: 광주-기아 챔피언스 필드, KIA 홈구장
- DAEGU: 대구 삼성 라이온즈 파크, 삼성 홈구장
- SUWON: 수원 KT 위즈파크, KT 홈구장
- DAEJEON: 대전 한화생명 볼파크, 한화 홈구장
- JAMSIL: 잠실야구장, LG/두산 홈구장
- CHANGWON: 창원NC파크, NC 홈구장

guide_types:
- stadium_bag_policy: 반입 금지 물품, 캔/병/음식물, 안전 정책, 준비물
- stadium_facility_guide: 편의시설, 매장, 구장샵, 화장실, 수유실 등
- stadium_seat_guide: 좌석 종류, 원정석, 응원석, 시야, 좌석 구역
- stadium_transport_guide: 지하철, 버스, 주차, 교통, 길찾기

호출해야 하는 경우:
- "사직구장 처음 가는데 뭐 챙겨야 해?"
- "잠실야구장 주차요금 얼마야?"
- "대전 한화생명 볼파크 좌석 알려줘"
- "고척돔 음식물 반입 가능해?"
- "문학구장 랜더스샵 위치 알려줘"

호출하지 않는 경우:
- 특정 날짜 경기 일정, 경기 유무, 경기 상태 질문은 find_kbo_game을 사용한다.
- 예매처, 예매 방법, 티켓 취소, 현장 발권 질문은 search_ticketing_guide를 사용한다.
- 야구 규칙, 플레이 설명, 최신 KBO 규정 질문은 search_baseball_knowledge를 사용한다.
- 실시간 티켓 잔여석, 실시간 주차 가능 대수, 날씨/우천 취소 예측은 현재 지원하지 않는다.
- 질문에서 구장이나 팀을 추론할 수 없고 favorite_team_id도 없으면 clarification을 요청한다.
""".strip()


SEARCH_TICKETING_GUIDE_TOOL_CARD = """
도구명: search_ticketing_guide

역할:
- KBO 구장/팀의 예매처, 예매 방법, 티켓 취소, 현장 발권, 예매 주의사항을 RAG 문서에서 검색한다.
- 기존 구장 가이드 RAG 중 stadium_ticketing_guide 문서만 검색한다.
- 실시간 잔여석, 현재 판매 가능 여부, 확정 가격은 조회하지 않는다.

입력:
- stadium_id: 필수 KBO 구장 ID
- team_id: 팀 맥락이 있으면 KBO 팀 ID, 없으면 null
- query: 사용자의 원문 질문
- top_k: 기본 5

구장 ID:
- SAJIK: 사직야구장, 롯데 홈구장
- GOCHEOK: 고척스카이돔, 키움 홈구장
- MUNHAK: 인천 SSG 랜더스필드, 문학구장, SSG 홈구장
- GWANGJU: 광주-기아 챔피언스 필드, KIA 홈구장
- DAEGU: 대구 삼성 라이온즈 파크, 삼성 홈구장
- SUWON: 수원 KT 위즈파크, KT 홈구장
- DAEJEON: 대전 한화생명 볼파크, 한화 홈구장
- JAMSIL: 잠실야구장, LG/두산 홈구장
- CHANGWON: 창원NC파크, NC 홈구장

호출해야 하는 경우:
- "사직 예매 어디서 해?"
- "롯데 경기 예매 방법 알려줘"
- "고척돔 티켓 취소 가능해?"
- "창원NC파크 현장 발권 돼?"
- "문학구장 티켓은 어디서 사?"
- "대전 한화생명 볼파크 예매 주의사항 알려줘"

호출하지 않는 경우:
- 실시간 잔여석, 현재 티켓 판매 여부, 특정 좌석 재고 질문
- 좌석 시야/구역/추천 질문
- 경기 일정, 경기 유무, 경기 상태 질문
- 질문에서 구장이나 팀을 추론할 수 없고 favorite_team_id도 없으면 clarification을 요청한다.

미지원 분류:
- 실시간 티켓 잔여 여부: ticket_inventory_tool_required
""".strip()


GET_WEATHER_CONTEXT_TOOL_CARD = """
도구명: get_weather_context

역할:
- KBO 구장 기준의 현재 실황 또는 오늘~글피 날씨 예보를 조회한다.
- 강수, 기온, 습도, 바람을 바탕으로 직관 준비와 주의 수준을 반환한다.
- 우천 취소 여부를 확정하지 않고, 좌석별 쾌적도도 확정하지 않는다.

입력:
- stadium_id: 필수 KBO 구장 ID
- date: 필수 조회 날짜. 오늘부터 글피까지만 지원한다.
- time: 경기 시작 시각 또는 사용자가 물은 시각. 없으면 null
- purpose: game_weather 또는 visit_weather

구장 ID:
- SAJIK: 사직야구장, 롯데 홈구장
- GOCHEOK: 고척스카이돔, 키움 홈구장
- MUNHAK: 인천 SSG 랜더스필드, 문학구장, SSG 홈구장
- GWANGJU: 광주-기아 챔피언스 필드, KIA 홈구장
- DAEGU: 대구 삼성 라이온즈 파크, 삼성 홈구장
- SUWON: 수원 KT 위즈파크, KT 홈구장
- DAEJEON: 대전 한화생명 볼파크, 한화 홈구장
- JAMSIL: 잠실야구장, LG/두산 홈구장
- CHANGWON: 창원NC파크, NC 홈구장

호출해야 하는 경우:
- "오늘 사직 비 와?"
- "내일 잠실 날씨 어때?"
- "대전 한화생명 볼파크 날씨 알려줘"
- "고척돔이면 비 와도 괜찮아?"
- "오늘 경기 우천 취소될까?"
- "오늘 날씨면 직관 가기 괜찮아?"
- "오늘 너무 더우면 야구장 가기 힘들까?"

호출하지 않는 경우:
- 과거 날씨 질문
- 글피 이후 장기예보 질문
- 특정 경기의 공식 우천 취소 발표 여부 또는 취소 확정 요구
- 질문에서 구장이나 팀을 추론할 수 없고 favorite_team_id도 없으면 clarification을 요청한다.

미지원 분류:
- 과거 날씨 또는 글피 이후 장기예보: weather_forecast_range_not_supported
- 특정 경기의 공식 우천 취소 발표 여부 또는 취소 확정 요구: weather_or_realtime_cancellation_prediction_required
""".strip()


AGENT_TOOL_SPECS: Mapping[ToolName, AgentToolSpec] = {
    "find_kbo_game": AgentToolSpec(
        name="find_kbo_game",
        routing_args_type=FindKboGameRoutingArgs,
        tool_input_type=FindKboGameToolInput,
        executor_handler_attr="_find_kbo_game_handler",
        display_label="경기 일정",
        routing_card=FIND_KBO_GAME_TOOL_CARD,
    ),
    "search_baseball_knowledge": AgentToolSpec(
        name="search_baseball_knowledge",
        routing_args_type=SearchBaseballKnowledgeRoutingArgs,
        tool_input_type=SearchBaseballKnowledgeToolInput,
        executor_handler_attr="_search_baseball_knowledge_handler",
        display_label="야구 지식",
        routing_card=SEARCH_BASEBALL_KNOWLEDGE_TOOL_CARD,
    ),
    "get_stadium_info": AgentToolSpec(
        name="get_stadium_info",
        routing_args_type=GetStadiumInfoRoutingArgs,
        tool_input_type=GetStadiumInfoToolInput,
        executor_handler_attr="_get_stadium_info_handler",
        display_label="구장 정보",
        routing_card=GET_STADIUM_INFO_TOOL_CARD,
    ),
    "search_ticketing_guide": AgentToolSpec(
        name="search_ticketing_guide",
        routing_args_type=SearchTicketingGuideRoutingArgs,
        tool_input_type=SearchTicketingGuideToolInput,
        executor_handler_attr="_search_ticketing_guide_handler",
        display_label="예매 안내",
        routing_card=SEARCH_TICKETING_GUIDE_TOOL_CARD,
    ),
    "search_stadium_guide": AgentToolSpec(
        name="search_stadium_guide",
        routing_args_type=SearchStadiumGuideRoutingArgs,
        tool_input_type=SearchStadiumGuideToolInput,
        executor_handler_attr="_search_stadium_guide_handler",
        display_label="구장 가이드",
        routing_card=SEARCH_STADIUM_GUIDE_TOOL_CARD,
    ),
    "get_weather_context": AgentToolSpec(
        name="get_weather_context",
        routing_args_type=GetWeatherContextRoutingArgs,
        tool_input_type=GetWeatherContextToolInput,
        executor_handler_attr="_get_weather_context_handler",
        display_label="구장 날씨",
        routing_card=GET_WEATHER_CONTEXT_TOOL_CARD,
    ),
}


def get_agent_tool_spec(tool_name: str) -> AgentToolSpec | None:
    return AGENT_TOOL_SPECS.get(tool_name)


def get_routing_tool_cards() -> list[str]:
    return [spec.routing_card for spec in AGENT_TOOL_SPECS.values()]
