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
- KBO 홈구장의 예매 방법, 좌석, 반입 정책, 교통, 주차, 편의시설 안내를 RAG 문서에서 검색한다.
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
- stadium_ticketing_guide: 예매처, 예매 방법, 취소, 현장 발권
- stadium_transport_guide: 지하철, 버스, 주차, 교통, 길찾기

호출해야 하는 경우:
- "사직구장 처음 가는데 뭐 챙겨야 해?"
- "잠실야구장 주차요금 얼마야?"
- "창원NC파크 예매는 어디서 해?"
- "대전 한화생명 볼파크 좌석 알려줘"
- "고척돔 음식물 반입 가능해?"
- "문학구장 랜더스샵 위치 알려줘"

호출하지 않는 경우:
- 특정 날짜 경기 일정, 경기 유무, 경기 상태 질문은 find_kbo_game을 사용한다.
- 야구 규칙, 플레이 설명, 최신 KBO 규정 질문은 search_baseball_knowledge를 사용한다.
- 실시간 티켓 잔여석, 실시간 주차 가능 대수, 날씨/우천 취소 예측은 현재 지원하지 않는다.
- 질문에서 구장이나 팀을 추론할 수 없고 favorite_team_id도 없으면 clarification을 요청한다.
""".strip()


TOOL_ROUTING_TOOL_CARDS = [
    FIND_KBO_GAME_TOOL_CARD,
    SEARCH_BASEBALL_KNOWLEDGE_TOOL_CARD,
    GET_STADIUM_INFO_TOOL_CARD,
    SEARCH_STADIUM_GUIDE_TOOL_CARD,
]
