# Weather Tool Implementation Next Steps

> 작성일: 2026-08-02  
> 목적: 다음 세션에서 `get_weather_context` Tool 구현을 바로 시작하기 위한 메모  
> 현재 기준 커밋: `b10aa43 test: add baseball knowledge search evaluation`  
> 중요: 사용자가 `backend/.env`에 KMA 설정을 추가해둔 상태다.

## 1. 현재 Tool 상태

현재 구현 및 Agent routing/executor 연결이 끝난 Tool은 4개다.

```text
find_kbo_game
get_stadium_info
search_stadium_guide
search_baseball_knowledge
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

search_stadium_guide
- 예매/좌석/반입/교통/편의시설 등 설명형 구장 가이드 RAG Tool
- 전체 9개 정규 홈구장 45개 chunk 임베딩/upsert 완료
- routing 연결됨
- executor 연결됨
- 대표 Tool 케이스 10/10 통과 기록 있음

search_baseball_knowledge
- 공식야구규칙/KBO 리그 규정/자주 나오는 플레이 설명 RAG Tool
- 27개 chunk 임베딩/upsert 완료
- routing 연결됨
- executor 연결됨
- 검색 평가셋 20개 기준 top3_topic_accuracy=1.0
```

## 2. 다음 Tool

다음 신규 Tool은 기상청 단기예보 조회서비스 기반 날씨 Tool이다.

추천 Tool 이름:

```text
get_weather_context
```

역할:

```text
구장 또는 경기 기준의 날씨 정보를 조회해 직관 컨디션 판단에 사용할 정형 weather context를 반환한다.
초기 범위는 "오늘 이 날씨에 직관 가기 괜찮은가"를 판단하는 보조 정보 제공이다.
좌석별 추천이나 좌석별 쾌적도 판단까지 확장하지 않는다.
```

예상 사용자 질문:

```text
오늘 사직 비 와?
내일 잠실 경기 우천 취소될까?
대전 한화생명 볼파크 날씨 알려줘
오늘 롯데 경기장 날씨 어때?
고척돔이면 비 와도 괜찮아?
오늘 날씨면 직관 가기 괜찮아?
오늘 너무 더우면 야구장 가기 힘들까?
```

주의:

```text
날씨 Tool은 우천 취소를 확정하지 않는다.
강수/기온/풍속/습도 등 기상 context와 한계를 제공한다.
실제 경기 취소 여부는 find_kbo_game의 game_status 또는 공식 발표를 확인해야 한다.
좌석 추천 Tool이 아니며, 좌석별 지붕/그늘/시야/쾌적도를 확정하지 않는다.
비, 더위, 습도, 바람을 바탕으로 직관 준비와 주의 수준만 알려준다.
기상청 단기예보 조회서비스에서 조회 가능한 기간까지만 지원한다.
초기 지원 범위는 현재 실황과 오늘~글피 예보다.
과거 날씨, 글피 이후 장기예보, 시즌 전체/이번 주말 범위 중 조회 가능 기간을 넘는 날씨는 지원하지 않는다.
```

## 3. KMA API 설정

사용자가 이전 프로젝트에서 받아둔 공공데이터포털 KMA 값을 현재 `.env`에 추가해둔 상태다.

확정 env 이름:

```env
KMA_API_ENDPOINT=https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0
KMA_SERVICE_KEY=...
```

공식 서비스:

```text
기상청_단기예보 조회서비스
Service URL: https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0
```

사용 가능한 상세 API:

```text
getUltraSrtNcst  # 초단기실황
getUltraSrtFcst  # 초단기예보
getVilageFcst    # 단기예보
getFcstVersion   # 예보버전
```

요청 파라미터 인증키 이름:

```text
ServiceKey
```

코드에서는 env `KMA_SERVICE_KEY`를 읽고, HTTP 요청에서는 `ServiceKey=<value>`로 전달한다.

`backend/.env.example`에도 아래 값을 추가해야 한다.

```env
KMA_API_ENDPOINT=https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0
KMA_SERVICE_KEY=
```

## 4. 입력 Schema 초안

처음에는 단순하게 시작한다.

```json
{
  "stadium_id": "SAJIK",
  "team_id": "LOTTE",
  "date": "2026-08-02",
  "time": "18:30",
  "purpose": "visit_weather"
}
```

필드:

```text
stadium_id: 필수 권장. 구장 nx/ny 조회에 사용
team_id: 선택. stadium_id가 없을 때 홈구장 추론에 사용 가능
date: 필수. 조회 날짜
time: 선택. 경기 시작 시각 또는 사용자가 물은 시각
purpose: game_weather | visit_weather
```

초기 구현에서는 `stadium_id`와 `date`를 필수로 두는 편이 안전하다.

## 5. 출력 Schema 초안

```json
{
  "stadium_id": "SAJIK",
  "stadium_name": "부산 사직 야구장",
  "date": "2026-08-02",
  "time": "18:30",
  "weather": {
    "temperature_c": 28.1,
    "precipitation_probability": 60,
    "precipitation_mm": 1.0,
    "sky": "cloudy",
    "wind_speed_mps": 2.4,
    "humidity_percent": 80
  },
  "visit_condition": {
    "level": "caution",
    "reasons": [
      "precipitation_probability_high",
      "humidity_high"
    ],
    "tips": [
      "우비나 방수 가능한 겉옷을 준비하세요.",
      "실제 경기 진행 여부는 공식 경기 상태를 함께 확인하세요."
    ]
  },
  "source": {
    "provider": "KMA",
    "base_time": "2026-08-02T17:00:00+09:00",
    "api": "기상청 단기예보"
  },
  "limitations": [
    "weather_forecast_not_game_cancellation_decision",
    "seat_specific_comfort_not_supported"
  ]
}
```

## 6. 구장 격자 좌표 문제

현재 `kbo_stadiums`에는 다음 컬럼이 있다.

```text
latitude
longitude
```

하지만 migration/seed 기준으로 현재 값은 `null`이다.

초기 구현은 DB 좌표 대신 코드 상수로 간다.

```text
stadium_id -> KMA nx/ny
```

구현 파일 후보:

```text
backend/app/domains/baseball/tool/get_weather_context/stadium_grid.py
```

정규 홈구장 9개는 우선 모두 넣는다.

```text
SAJIK
GOCHEOK
MUNHAK
GWANGJU
DAEGU
SUWON
DAEJEON
JAMSIL
CHANGWON
```

`POHANG`은 schedule/routing schema에는 있지만 정규 홈구장 범위가 아니므로 초기에는 미지원 또는 fallback으로 둔다.

## 7. 구현 위치

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
backend/app/core/config.py
backend/.env.example
backend/app/api/dependencies.py
backend/app/agent/routing_schemas.py
backend/app/agent/tool_cards.py
backend/app/agent/prompts.py
backend/app/agent/tool_executor.py
data/kbo_schedule/evaluation/cases/find_kbo_game_cases.jsonl
```

## 8. 구현 순서

```text
1. Settings에 KMA 설정 추가
   - kma_api_endpoint: str
   - kma_service_key: str

2. backend/.env.example에 KMA env 추가

3. stadium_grid.py 작성
   - stadium_id -> nx/ny 매핑
   - 알 수 없는 stadium_id 오류 처리

4. kma_client.py 작성
   - http client 선택: httpx 권장
   - getUltraSrtNcst / getUltraSrtFcst / getVilageFcst 중 초기 범위 결정
   - dataType=JSON 사용
   - ServiceKey, base_date, base_time, nx, ny 처리

5. base_date/base_time 계산 규칙 구현
   - 초단기실황/초단기예보/단기예보별 발표시각 차이를 확인
   - 초기에는 단기예보 또는 초단기예보 하나만 먼저 붙여도 됨

6. KMA category 매핑
   - TMP/T1H: 기온
   - POP: 강수확률
   - PCP/RN1: 강수량
   - SKY: 하늘상태
   - WSD: 풍속
   - REH: 습도
   - PTY: 강수형태

7. schemas.py 작성
   - input/result/weather/visit_condition/source/limitations 모델

8. handler.py 작성
   - stadium_id/date/time 입력
   - stadium grid 조회
   - KMA client 호출
   - Tool result로 정규화
   - 강수/기온/습도/풍속 기반 visit_condition 산출
   - 고척돔이면 돔구장 맥락을 visit_condition reasons/tips에 반영
   - 좌석별 추천은 하지 않고 limitation에 seat_specific_comfort_not_supported 포함

9. AgentToolExecutor / dependencies 연결

10. routing_schemas/tool_cards/prompts에 get_weather_context 추가

11. routing 평가 케이스 추가

12. 실제 API 호출 1~2건 수동 확인
```

## 9. 라우팅 정책 초안

`get_weather_context` 호출:

```text
구장 또는 경기 장소 기준의 날씨, 비, 기온, 바람, 습도, 직관 컨디션 질문
```

예:

```text
오늘 사직 비 와?
내일 잠실 날씨 어때?
대전 한화생명 볼파크 날씨 알려줘
고척돔이면 비 와도 괜찮아?
오늘 날씨면 직관 가기 괜찮아?
오늘 너무 더우면 야구장 가기 힘들까?
```

`find_kbo_game`과 조합이 필요한 경우:

```text
오늘 롯데 경기장 날씨 어때?
```

이상적인 흐름:

```text
find_kbo_game으로 오늘 롯데 경기의 stadium_id/start_time 확인
→ get_weather_context로 해당 구장/시간 날씨 조회
```

다만 현재 Agent orchestration은 multi-step Tool chain이 아직 없다.

초기 routing 정책:

```text
질문에 stadium_id를 직접 추론할 수 있으면 get_weather_context
질문에 팀과 날짜만 있으면 우선 find_kbo_game 또는 clarification
특정 경기의 우천 취소 확정 예측은 지원하지 않고 weather context만 제공
날씨 때문에 직관이 괜찮은지 묻는 질문은 get_weather_context로 처리
좌석 추천 질문은 weather Tool만으로 확정하지 않음
```

## 10. 완료 기준

```text
1. get_weather_context Tool schema/handler/client 구현
2. API key 없을 때 명확한 오류
3. 구장별 날씨 조회가 최소 1건 성공
4. Tool 결과에 provider/base_time/api/limitations 포함
5. 고척돔은 stadium_id/is_dome 맥락을 유지
6. routing에서 날씨 질문이 get_weather_context로 분류됨
7. 우천 취소를 확정하지 않는 limitation이 항상 포함됨
8. 직관 컨디션 level/reasons/tips를 반환함
9. 좌석별 추천을 확정하지 않는 limitation이 포함됨
```

## 11. 다음 세션 시작 명령

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball
git status --short
git log --oneline -5
sed -n '1,260p' docs/memo/2026-08-02-weather-tool-implementation-next-steps.md
```
