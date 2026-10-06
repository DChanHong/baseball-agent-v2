# 일반 채팅 API의 표본 Faithfulness 평가

> 작성일: 2026-10-05
> 상태: API 연결·합성 통합 검증 완료 / DB·실제 채팅 API의 유료 E2E 실행 미실시
> 선행: [평가 계약](2026-10-05-ragas-evaluation-contract-spec.md), [지표 API smoke](../work/2026-10-05-ragas-synthetic-metric-demo.md)

## 1. 적용 범위

- [확인됨] `/api/v1/chat`의 구장·예매·야구 지식 RAG 답변 중 근거가 있고 `answerability`가 insufficient_source가 아닌 모델 답변을 대상으로 한다.
- [확인됨] 기본 5% 확률로 Faithfulness만 평가한다. 경기·날씨·직접 follow-up·template·fallback·빈 근거는 제외한다. 이들의 발생 원인과 답변 경로는 기존 agent trace를 사용한다.
- [확인됨] 모든 요청의 기존 schema·evidence ref·limitation 검사와 서버 검수 안내는 유지한다. 평가 점수로 사용자 답변을 수정하거나 차단하지 않는다.
- [확인됨] 운영에 필요한 `ragas==0.4.3`과 호환용 `langchain-community==0.4.1`을 runtime dependencies로 이동했다. 일반 `uv sync --locked`에 포함된다.

## 2. 데이터와 처리 흐름

[답변 생성 서비스](../../backend/app/agent/answer_generation_service.py)는 정상 계약 검증 후 원래 모델 답변과 실제 bounded evidence를 메모리에 캡처한다. 서버가 붙인 검수 안내는 평가 답변에서 제외하고 기존 정책 처리로 유지한다. 상위 3개·본문 각각 6,000자의 기존 제한을 다시 늘리거나 잘리기 전 검색 원문을 추가하지 않는다.

[답변 schema](../../backend/app/agent/answer_schemas.py)의 `_evaluation_input`은 PrivateAttr이며 모델 출력 JSON Schema·`model_dump`·DB metadata·SSE에 포함되지 않는다. 사용자 질문과 답변·근거는 평가 요청을 위해 메모리에서만 잠시 사용한다. 새로운 운영 대화/평가 원문 파일이나 DB 저장은 추가하지 않았다.

[chat service](../../backend/app/domains/chat/service/services.py)가 완료된 답변 입력을 전달하고, [router](../../backend/app/domains/chat/controller/router.py)의 Starlette BackgroundTask가 **최종 SSE body 전송 이후** 평가를 제출한다. background callback은 평가 완료를 기다리지 않고 별도 asyncio task를 생성한다. 미완료 stream·중복 callback은 평가하지 않는다. 평가 실패는 사용자 SSE에 실패 이벤트를 추가하지 않는다.

[평가 모듈](../../backend/app/agent/online_evaluation.py)은 worker 프로세스당 평가 1개만 동시에 수행한다. 평가 중 새 표본은 worker_busy로 제외하며 대화 원문을 대기열에 쌓지 않는다. 따라서 실제 평가 비율은 트래픽·비용 상한에 따라 5%보다 낮을 수 있다. 생성 task는 요청의 ContextVar를 상속하지 않는다. [앱 lifespan](../../backend/app/main.py)은 종료 시 평가 task를 취소·정리한다. 강제 종료 시 실행 중 평가가 유실될 수 있는 best-effort 방식이다.

## 3. 비용 제어

judge는 `gpt-4o-mini-2024-07-18`, temperature 0, 호출당 출력 상한 1,024 token이다. embedding을 호출하지 않는다. Faithfulness의 주장 추출·근거 대조로 답변당 최대 2회 judge HTTP 요청만 허용한다. SDK·Instructor·runner 재시도는 모두 0이다. API 요청 timeout은 20초, 전체 평가 timeout은 기본 45초다.

비용은 실제 청구금액이 아니라 **보수적인 사전 예약 추정치**로 제한한다. 각 HTTP 호출 직전에 요청 body byte 수와 chat framing 여유 1,024 token, 최대 출력 1,024 token으로 input/output 비용을 예약한다. 100만 token당 input $0.15·output $0.60을 사용하며 캐시 할인을 가정하지 않는다. 모델·endpoint·출력 상한이 달라지거나 body가 128,000 byte를 초과하면 호출하지 않는다. 단가/모델 변경 시 이 계산도 재검증해야 한다.

장부는 `logs/ragas-budget.json`에 `day`, `reserved_microusd`만 저장한다. 일일 기본 상한은 $0.10이며 날짜는 Asia/Seoul 기준이다. 실패·timeout·중단된 호출도 예약 금액을 반환하지 않으므로 실제 사용액보다 일찍 제한에 도달할 수 있다. 두 번째 호출 예산이 부족하면 첫 호출 뒤 지표 계산이 제외될 수 있다.

파일 잠금과 fsync로 같은 파일을 쓰는 동일 호스트 worker의 예약을 직렬화한다. 재시작해도 파일이 유지되면 현재 날짜의 한도를 공유한다. 장부 손상·쓰기 실패는 평가를 차단한다. 상한은 애플리케이션의 추정 단가와 예약 기준이며 OpenAI 계정의 전체 청구 한도가 아니다.

**운영 범위:** Unix 파일 잠금 기반이며 같은 영속 파일을 공유하는 단일 호스트 배포에 적용한다. 컨테이너에서는 영속 volume을 사용하고, 장부 파일을 삭제/초기화하지 않는다. 별도 파일을 쓰는 여러 호스트에서는 각 호스트가 별도 상한을 갖는다. 다중 호스트 전체에 $0.10을 적용하려면 공유 예산 서비스가 필요하다. 이번 작업은 DB migration이나 별도 외부 큐를 도입하지 않았다.

## 4. 설정과 관측

[설정](../../backend/app/core/config.py) 및 [환경변수 예시](../../backend/.env.example):

```dotenv
RAGAS_ONLINE_ENABLED=true
RAGAS_ONLINE_SAMPLE_RATE=0.05
RAGAS_ONLINE_DAILY_BUDGET_USD=0.10
RAGAS_ONLINE_BUDGET_PATH=logs/ragas-budget.json
RAGAS_ONLINE_TIMEOUT_SECONDS=45
```

설정 변경은 서버를 재시작해 적용한다. `RAGAS_ONLINE_ENABLED=false` 또는 sample rate 0으로 평가를 끈다. 기존 `OPENAI_API_KEY`를 사용하고 별도 RAGAS KEY는 필요 없다. 코드에 키를 저장하거나 로그에 출력하지 않는다.

새 평가 로그는 `ragas_online` JSON으로 metric·status·score·duration_ms·error_code만 기록한다. 사용자/대화 ID·질문·답변·근거·judge 이유·예외 전문은 남기지 않는다. judge 라이브러리의 내부 로깅은 억제하고 RAGAS analytics는 비활성화한다. 기존 앱의 HTTP/대화 저장 정책을 일괄 변경한 작업은 아니다.

```bash
cd backend
uv sync --locked
rg 'ragas_online' /private/tmp/baseball-backend.log
RAGAS_DO_NOT_TRACK=true .venv/bin/python -m pytest -q
```

예산/요청 제한은 excluded, judge 오류·timeout·장부 접근 실패는 error로 기록한다. 계산하지 못한 점수는 null이다. 점수 0은 계산된 결과로 구분한다.

## 5. 검증과 잔여 범위

- [확인됨] 전용 테스트는 5% 경계값, 비활성화·비RAG 제외, 단일 실행 제한, 재시작·동시 파일 예약·날짜 변경·장부 손상, 네트워크 전 예산 차단, 실패 예약 유지·최대 2회 호출을 검증한다.
- [확인됨] 실제 RAGAS·OpenAI SDK 경로를 MockTransport로 실행해 점수 계산과 예산 예외 wrapping을 검증했다. 무효 judge 출력은 재시도 없이 종료하고 원문이 로그에 없는지 검사했다.
- [확인됨] ASGI 응답의 마지막 body 이후 제출, 평가 private 입력의 DB metadata 미포함, 미완료 stream 미제출을 검증했다. 후처리 전 답변과 6,000자 근거 제한 캡처를 검사했다.
- [확인됨] 변경 파일 Ruff 및 새 평가 모듈 mypy 통과. 관련 모듈 확장 타입 검사는 HEAD snapshot과 현재 모두 기존 오류 23개이며 추가 오류가 없다.
- [확인됨] 최종 backend 전체 테스트 141개 통과. 기존 chat 평가 데이터 validator는 cases 30·candidates 5·manual runs 2개 정합성을 확인했다. 문서 링크·runtime lock 의존성 연결·git diff 공백 검사도 통과했다.
- [확인 필요] DB·실제 사용자 채팅·브라우저·유료 API를 묶은 E2E 검증, 운영 sample 분포와 점수 해석. 이번 회차에는 해당 실행이나 배포·commit·push를 하지 않았다.

일반 채팅에 Precision/Recall/Relevancy를 추가하지 않았다. 검수 reference를 사용하는 전체 baseline runner와 세 RAG Tool 평가셋 보강은 [다음 작업 메모](../memo/v2/2026-10-05-ragas-evaluation-baseline-next-steps.md)의 별도 과제다.
