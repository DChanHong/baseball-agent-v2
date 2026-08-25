# Weather Tool Next Steps

> 작성일: 2026-07-30  
> 목적: 다음 세션에서 기상청 API 기반 날씨 Tool 작업을 바로 이어가기 위한 메모  
> 현재 기준 커밋: `7cad7cd feat: add stadium info tool`

## 1. 현재 Tool 상태

현재 3개 Tool은 구현 및 routing/executor 연결까지 완료됐다.

```text
find_kbo_game
get_stadium_info
search_stadium_guide
```

상태 요약:

```text
find_kbo_game
- 경기 일정/상태/장소/점수 조회 Tool
- routing 연결됨
- executor 연결됨

get_stadium_info
- 구장 주소, 지역, 홈팀, 돔 여부 등 정형 구장 정보 조회 Tool
- routing 연결됨
- executor 연결됨
- 단, 추가 후 별도 테스트/평가는 아직 실행하지 않음

search_stadium_guide
- 예매/좌석/반입/교통/편의시설 등 설명형 구장 가이드 RAG Tool
- 전체 9개 정규 홈구장 45개 chunk 임베딩/upsert 완료
- routing 연결됨
- executor 연결됨
- 대표 Tool 케이스 10/10 통과
```

## 2. 로컬 Supabase 임베딩 데이터 주의

현재 로컬 Supabase `rag_documents`, `rag_chunks`에는 전체 구장 가이드 임베딩이 upsert되어 있다.

유지되는 경우:

```text
컴퓨터 종료/재시작
supabase stop
supabase start
```

사라지는 경우:

```text
supabase db reset
Docker volume 삭제
```

`supabase db reset`을 실행하면 RAG 임베딩 데이터는 seed에 포함되어 있지 않으므로 다시 실행해야 한다.

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend
uv run python scripts/generate_stadium_guide_chunks.py --stadium-id all
uv run python scripts/embed_stadium_guide_chunks.py
```

## 3. 다음 Tool: get_weather_context

다음 작업은 기상청 API 기반 날씨 Tool이다.

추천 Tool 이름:

```text
get_weather_context
```

역할:

```text
구장 또는 경기 기준의 날씨 정보를 조회해 Agent 답변에 사용할 정형 weather context를 반환한다.
```

예상 사용자 질문:

```text
오늘 사직 비 와?
내일 잠실 경기 우천 취소될까?
대전 한화생명 볼파크 날씨 알려줘
오늘 롯데 경기장 날씨 어때?
고척돔이면 비 와도 괜찮아?
```

주의:

```text
날씨 Tool은 우천 취소를 확정하지 않는다.
강수/기온/풍속 등 기상 context와 한계를 제공한다.
실제 경기 취소 여부는 find_kbo_game의 game_status 또는 공식 발표를 확인해야 한다.
```

## 4. 입력 Schema 초안

처음에는 단순하게 시작한다.

```json
{
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "date": "2026-07-31",
  "time": "18:30",
  "purpose": "game_weather"
}
```

필드:

```text
stadium_id: 필수 권장. 구장 좌표/지역 조회에 사용
team_id: 선택. stadium_id가 없을 때 홈구장 추론에 사용 가능
date: 필수. 조회 날짜
time: 선택. 경기 시작 시각 또는 사용자가 물은 시각
purpose: game_weather | stadium_visit_weather
```

초기 구현에서는 `stadium_id`와 `date`를 필수로 두는 편이 안전하다.

## 5. 출력 Schema 초안

```json
{
  "stadium_id": "SAJIK",
  "stadium_name": "부산 사직 야구장",
  "date": "2026-07-31",
  "time": "18:30",
  "weather": {
    "temperature_c": 28.1,
    "precipitation_probability": 60,
    "precipitation_mm": 1.0,
    "sky": "cloudy",
    "wind_speed_mps": 2.4,
    "humidity_percent": 80
  },
  "source": {
    "provider": "KMA",
    "base_time": "2026-07-31T17:00:00+09:00",
    "api": "기상청 단기예보"
  },
  "limitations": [
    "weather_forecast_not_game_cancellation_decision"
  ]
}
```

## 6. 기상청 API 검토 포인트

사용 후보:

```text
기상청 단기예보 조회서비스
- 초단기실황
- 초단기예보
- 단기예보
```

확인할 것:

```text
1. API key 환경변수 이름
2. 요청 URL과 인증 방식
3. 날짜/시간별 base_date, base_time 계산 규칙
4. nx, ny 격자 좌표 필요 여부
5. 경기장 위도/경도를 기상청 격자 좌표로 변환하는 함수 필요 여부
6. 응답 category 매핑
7. API 장애/데이터 없음 처리
```

환경변수 후보:

```text
KMA_API_KEY
KMA_BASE_URL
```

`backend/.env.example`에도 추가해야 한다.

## 7. 구장 좌표 문제

현재 `kbo_stadiums`에는 다음 컬럼이 있다.

```text
latitude
longitude
```

하지만 migration 기준으로 현재 값은 `null`로 들어간다.

따라서 다음 중 하나가 필요하다.

```text
A. kbo_stadiums latitude/longitude를 공식/검증 출처로 채운다.
B. 기상청 nx/ny 격자 좌표를 stadium metadata에 직접 저장한다.
C. 코드 상수로 stadium_id -> nx/ny 매핑을 먼저 둔다.
```

빠른 구현 추천:

```text
C. 코드 상수로 9개 정규 홈구장 nx/ny를 먼저 둔다.
```

이후 좌표 출처가 정리되면 DB 컬럼 또는 metadata로 이동한다.

## 8. 구현 위치 제안

기존 Tool 구조에 맞춘다.

```text
backend/app/domains/baseball/tool/get_weather_context/
  __init__.py
  schemas.py
  handler.py
  kma_client.py
  stadium_grid.py
```

연결 파일:

```text
backend/app/agent/routing_schemas.py
backend/app/agent/tool_cards.py
backend/app/agent/prompts.py
backend/app/agent/tool_executor.py
backend/app/api/dependencies.py
backend/app/core/config.py
backend/.env.example
```

## 9. 구현 순서

```text
1. 기상청 API key/env 이름 확정
2. Settings에 KMA 설정 추가
3. stadium_id -> nx/ny 매핑 추가
4. KMA client 작성
5. get_weather_context schemas.py 작성
6. handler.py 작성
7. AgentToolExecutor 연결
8. routing_schemas/tool_cards/prompts에 get_weather_context 추가
9. 대표 routing cases 추가
10. 실제 API 호출 1~2건으로 수동 확인
```

사용자가 테스트를 원하지 않으면 10번은 생략한다.

## 10. 라우팅 정책 초안

`get_weather_context` 호출:

```text
구장 또는 경기 장소 기준의 날씨, 비, 기온, 바람, 습도 질문
```

`find_kbo_game`과 조합이 필요한 경우:

```text
오늘 롯데 경기장 날씨 어때?
```

이 경우 이상적인 흐름:

```text
find_kbo_game으로 오늘 롯데 경기의 stadium_id/start_time 확인
→ get_weather_context로 해당 구장/시간 날씨 조회
```

다만 현재 Agent orchestration은 multi-step Tool chain이 아직 없다.

초기 routing에서는 다음처럼 처리 가능하다.

```text
질문에 stadium_id를 직접 추론할 수 있으면 get_weather_context
질문에 팀과 날짜만 있으면 우선 find_kbo_game 또는 clarification
```

멀티스텝 Tool 실행은 답변 생성/Agent workflow 단계에서 별도 구현한다.

## 11. 완료 기준

```text
1. get_weather_context Tool schema/handler/client 구현
2. 구장별 날씨 조회가 최소 1건 성공
3. API key 없을 때 명확한 오류
4. 고척돔은 is_dome 정보를 함께 활용할 수 있도록 stadium_id 유지
5. Tool 결과에 provider/base_time/limitations 포함
6. routing에서 날씨 질문이 get_weather_context로 분류됨
```

## 12. 다음 세션 시작 명령

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball
git status --short
git log --oneline -5
sed -n '1,260p' docs/memo/2026-07-30-weather-tool-next-steps.md
```
