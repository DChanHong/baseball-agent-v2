# Weather Tool Stabilization and Verification

> 작성일: 2026-08-08  
> 목적: `get_weather_context` 테스트 안정화 및 실제 KMA API 검증 결과 기록

## 1. 테스트 안정화

`GetWeatherContextToolHandler`가 현재 시각을 직접 `datetime.now(KST)`로 읽고 있어,
테스트가 실제 날짜가 바뀌면 깨지는 문제가 있었다.

해결:

```text
GetWeatherContextToolHandler(now_provider=...)
```

를 선택적으로 주입할 수 있게 하고, 운영 기본값은 기존처럼 KST 현재 시각을 사용한다.

추가/보강한 테스트:

```text
- 오늘~글피 지원 범위 검증
- 단기예보 기반 visit_condition 산출
- 고척돔 dome context 유지
- 현재 시각 조회 시 초단기실황 사용
- KMA_SERVICE_KEY 누락 시 명확한 ValueError
```

검증 결과:

```text
backend/.venv/bin/python -m pytest backend/tests/api/test_get_weather_context_tool.py
7 passed

backend/.venv/bin/python -m pytest backend/tests/api
9 passed
```

## 2. 실제 KMA API 수동 검증

`backend/.env`의 KMA 설정을 사용하되, 서비스 키 값은 출력하지 않았다.

검증 대상:

```text
stadium_id=JAMSIL
nx=61
ny=126
date=2026-08-08
```

검증 결과:

```text
kma_endpoint_configured=True
kma_service_key_configured=True

nowcast_api=기상청 초단기실황
nowcast_base=2026-08-08T16:00:00+09:00
nowcast_items=8
nowcast_categories=PTY, REH, RN1, T1H, UUU, VEC, VVV, WSD

vilage_api=기상청 단기예보
vilage_base=2026-08-08T17:00:00+09:00
vilage_items=1000
vilage_categories=PCP, POP, PTY, REH, SKY, SNO, TMN, TMP, TMX, UUU, VEC, VVV, WAV, WSD
```

Handler 정규화 결과:

```json
{
  "supported": true,
  "source": {
    "provider": "KMA",
    "base_time": "2026-08-08T17:00:00+09:00",
    "api": "기상청 단기예보"
  },
  "weather": {
    "temperature_c": 32.0,
    "precipitation_probability": 20,
    "precipitation_mm": 0.0,
    "precipitation_type": "none",
    "sky": "mostly_cloudy",
    "wind_speed_mps": 3.8,
    "humidity_percent": 65
  },
  "visit_condition": {
    "level": "caution",
    "reasons": ["temperature_high"]
  }
}
```

항상 포함되는 limitation도 확인했다.

```text
- weather_forecast_not_game_cancellation_decision
- seat_specific_comfort_not_supported
- weather_query_supported_only_from_today_to_three_days_later
```

## 3. Weather Routing Smoke

Weather 관련 routing case 5개만 추출해 smoke 평가를 실행했다.

대상 case:

```text
fg_016 오늘 경기 우천 취소될까?
fg_033 오늘 사직 비 와?
fg_034 내일 잠실 경기 날씨 어때?
fg_035 고척돔이면 비 와도 괜찮아?
fg_036 다음 주 사직 날씨 알려줘
```

초기 smoke에서는 `fg_016`이 실패했다.

원인:

```text
"공식 우천 취소 여부/취소 확정"과
"취소될까?처럼 날씨 context로 답할 수 있는 질문"의 구분이 프롬프트에서 덜 선명했다.
```

수정:

```text
- 공식 우천 취소 "발표 여부" 또는 취소 "확정" 요구만 unsupported로 명확화
- "오늘 경기 우천 취소될까?"를 get_weather_context few-shot으로 추가
- get_weather_context tool card 호출 예시에 동일 질문 추가
```

수정 후 결과:

```text
backend/.venv/bin/python scripts/evaluate_tool_routing.py \
  --dataset /tmp/weather_routing_cases.jsonl \
  --prompt-version weather-tool-smoke-v2

total=5
is_in_scope_accuracy=1.0
should_call_tool_accuracy=1.0
tool_name_accuracy=1.0
args_accuracy=1.0
clarification_accuracy=1.0
unsupported_accuracy=1.0
exact_match_accuracy=1.0
failed_case_ids=-
```

저장된 run:

```text
data/kbo_schedule/evaluation/runs/tool_routing/find_kbo_game/2026-08-08_082720_gpt-5-mini_weather-tool-smoke-v2.json
```
