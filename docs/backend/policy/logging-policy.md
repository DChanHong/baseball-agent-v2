# 백엔드 로깅 정책

> 라벨: `REFERENCE`  
> 상태: 초안  
> 기준: Python 표준 `logging` + FastAPI + SQLAlchemy

## 1. 목적

백엔드 로그는 로컬 개발, 장애 원인 파악, LLM tool 호출 추적을 돕기 위해 남긴다.

로그는 동작 흐름과 오류를 설명해야 하며, API key, 전체 prompt, 사용자 메시지 전문처럼 민감하거나 과도한 데이터는 남기지 않는다.

## 2. 기본 원칙

- Python 표준 `logging`을 기본 로깅 도구로 사용한다.
- 앱 전역 설정은 `backend/app/core/logging.py`에서 관리한다.
- 각 모듈은 `logging.getLogger(__name__)`로 logger를 만든다.
- `APP_DEBUG=true`일 때는 `DEBUG`, 그 외 환경에서는 `INFO` 이상을 기본으로 한다.
- 로그 메시지는 사람이 읽기 쉬운 문장과 필요한 key-value 정보를 함께 담는다.

예:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "KBO games lookup completed team_id=%s count=%d",
    team_id,
    count,
)
```

## 3. 로그 레벨 기준

| 레벨 | 사용 기준 |
|---|---|
| `DEBUG` | 개발 중 내부 설정, client 생성, 분기 확인 |
| `INFO` | 정상적인 주요 유스케이스 시작/완료 |
| `WARNING` | 요청은 처리 가능하지만 비정상 또는 주의가 필요한 상황 |
| `ERROR` | 요청 처리 실패, 외부 API 실패, 복구 가능한 예외 |
| `CRITICAL` | 앱 지속 실행이 어려운 치명적 장애 |

예외를 잡아서 다시 발생시킬 때는 `logger.exception(...)`을 사용한다.

```python
try:
    ...
except Exception:
    logger.exception("find_kbo_game tool failed")
    raise
```

## 4. 남기는 정보

다음 정보는 로그로 남길 수 있다.

- 유스케이스 이름
- tool 이름
- `team_id`, `date`, `date_from`, `date_to` 같은 조회 조건
- 조회 결과 개수
- model 이름
- timeout 설정
- conversation/message 식별자
- 처리 시간
- 예외 타입과 stack trace

## 5. 남기지 않는 정보

다음 정보는 로그에 남기지 않는다.

- `OPENAI_API_KEY`
- Supabase secret key, service role key
- DB password가 포함된 전체 connection string
- 사용자 메시지 전문
- LLM prompt 전문
- LLM 응답 전문
- tool 결과 payload 전체
- 개인정보, 인증 토큰, 쿠키

필요한 경우에도 원문 대신 식별자, 개수, 길이, 요약 상태만 남긴다.

## 6. 현재 적용 범위

현재 로깅은 다음 범위에 적용한다.

| 파일 | 로그 목적 |
|---|---|
| `backend/app/core/logging.py` | 앱 전역 logging 설정 |
| `backend/app/main.py` | 앱 시작 시 logging 설정 적용 |
| `backend/app/core/llm.py` | OpenAI client 생성 설정 확인 |
| `backend/app/domains/baseball/service/services.py` | KBO 경기 조회 시작/완료 |
| `backend/app/domains/baseball/tool/find_kbo_game/handler.py` | LLM tool 호출 시작/완료/실패 |

## 7. 확장 방향

운영 환경에서 로그 수집이 필요해지면 표준 `logging`을 유지한 채 JSON formatter를 추가한다.

요청 단위 추적이 필요해지면 middleware에서 `request_id`를 생성하고, conversation/message id와 함께 로그 context로 전달한다.

OpenTelemetry, Sentry, Datadog 같은 외부 관측성 도구는 실제 배포 환경과 장애 대응 요구가 정해진 뒤 도입한다.
