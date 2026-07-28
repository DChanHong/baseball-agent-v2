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
- 일반 야구 규칙, 팀 역사, 응원 문화, 구장 준비물, 직관 팁 질문
- 현재 티켓 잔여 여부
- 날씨 또는 미래/실시간 우천 취소 예측
- 두 팀 간 맞대결 일정 필터

미지원 분류:
- 티켓 잔여 여부: ticket_inventory_tool_required
- 날씨 또는 미래/실시간 우천 취소 예측: weather_or_realtime_cancellation_prediction_required
- 두 팀 간 맞대결 일정: opponent_team_filter_not_supported_yet
""".strip()


TOOL_ROUTING_TOOL_CARDS = [
    FIND_KBO_GAME_TOOL_CARD,
]
