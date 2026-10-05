# Agent 최소 Observability Spec

> 작성일: 2026-10-05
> 범위: MVP2 Step 3의 첫 회차, Agent graph 실행 단위 trace
> 상태: 구현 및 합성 회귀 테스트 완료. 운영·실제 모델 기반 QA 미실행.

## 1. 목적과 구현 전 기준선

- [확인됨] `backend/app/agent/graph.py`는 route → Tool → state update → answer의 단일 Tool workflow다.
- [확인됨] 기존 routing/Tool/answer 로그와 SSE Tool 이벤트, assistant metadata가 존재한다.
- [확인됨] 기존 `latency_ms`는 전체 graph 실행 시간이며 개별 단계 지연을 분리하지 않는다.
- [확인됨] 기존 HTTP 응답 로깅의 request ID는 Agent 단계에 전달되지 않았다.
- [추론] 단계별 실행을 공통 ID로 연결하면 검색 지연과 답변 생성 지연을 구분하기 쉽다. 실제 운영 지연 개선 효과는 아직 측정하지 않았다.

## 2. 개선 설계와 이번 구현

- [확인됨] graph 실행마다 임의 UUID hex `trace_id`를 생성한다. 사용자·대화 ID를 trace 로그에 복사하지 않는다.
- [확인됨] `backend/app/core/agent_trace.py`가 표준 logging에 `agent_trace <JSON>`을 기록한다. 기존 콘솔 formatter는 유지한다.
- [확인됨] graph state로 ID를 전달하고, node 실행 안에서만 ContextVar를 설정·복원한다. 동시 요청과 consumer task의 context를 분리한다.
- [확인됨] `trace_id`, `answer_source`, `fallback_reason`은 기존 assistant metadata에 추가된다. 새 DB table이나 migration은 없다.
- [확인됨] graph 밖에서 RAG handler를 직접 호출하면 trace는 기록하지 않는다.

## 3. 이벤트 계약

공통 필드: `schema_version=1`, `trace_id`, `event`, UTC ISO `timestamp`.
종료 이벤트의 `duration_ms`는 monotonic clock으로 측정한다.

| 단계 | 시작·종료 | 부가 정보 |
|---|---|---|
| turn | started / completed / failed / interrupted | 전체 graph 시간, 답변 경로, fallback 사유 또는 예외 타입 |
| route | started / completed / failed | 선택 Tool, Tool 호출 여부, 추가 질문 여부 |
| tool | started / completed / failed | Tool 이름, 실패 예외 타입 |
| embedding | started / completed / failed | embedding 모델 |
| retrieval | started / completed / failed | effective top_k, threshold, 결과 수, chunk ID, distance, 결과 존재 여부 |
| answer | started / completed / failed | 답변 경로, fallback 사유, answerability, 사용 evidence ref |
| answer_llm | started / completed / failed | 답변 모델, 모델 호출 시간·예외 타입 |

`retrieval.answerable`은 기존 Tool의 결과 존재 여부와 동일하다. 질문 핵심에 답할 수 있는지 판정한 `answer.answerability`와 구분한다.
`answer_llm.completed`는 모델 호출 반환을 뜻한다. 후속 schema/evidence 검증 실패는 `answer.completed`의 fallback 사유에 나타난다.
`turn.completed`는 graph가 답변을 생성했다는 뜻이며, fallback도 포함한다. DB 저장 또는 SSE 전송 완료를 의미하지 않는다.

답변 경로:

- `llm`: 근거 기반 모델 답변
- `contextual_direct`: 선택 경기 context에서 직접 응답
- `template`: 추가 질문, 미지원 안내 또는 모델 미설정 상태의 기본 응답
- `fallback`: Tool 실패 또는 답변 생성·검증 실패 후 기본 응답

## 4. 실패와 중단

- [확인됨] routing 예외는 `route.failed`, `turn.failed`를 남기고 기존 예외 경로로 전달된다.
- [확인됨] Tool 예외는 `tool.failed` 후 기본 답변으로 종료된다. 기존 chat service의 rollback 처리도 유지한다.
- [확인됨] 답변 timeout은 `answer_llm.failed`의 `TimeoutError`와 최종 `answer_source=fallback`으로 구분한다.
- [확인됨] consumer가 완료 전에 stream을 닫으면 `turn.interrupted`를 기록한다.
- [확인됨] 검색 결과가 비어도 검색 실행은 completed이며 결과 수 0으로 구분한다.

## 5. 로그 데이터 범위

새 trace에는 사용자 질문·답변, prompt, Tool input/payload 전문, 검색 원문·URL, 사용자 ID, cookie, token, API key, 예외 메시지를 기록하지 않는다. 허용된 운영 필드만 호출부에서 전달한다.

이 정책은 새 trace에 대한 것이다. 기존 HTTP body logging 및 다른 logger의 exception stack trace를 일괄 정비한 결과는 아니다.
검색 문서 ID와 distance는 운영 metadata로 취급한다.

## 6. 확인 방법

기존 backend 실행 명령은 `docs/backend/local-development-commands.md`를 따른다. 콘솔 로그를 저장했다면:

```bash
rg 'agent_trace ' /private/tmp/baseball-backend.log
rg '<확인할 trace_id>' /private/tmp/baseball-backend.log
```

기존 assistant message metadata의 `trace_id`로 같은 실행 로그를 찾을 수 있다. SSE 계약과 frontend 화면은 변경하지 않았다.
Tool duration에는 embedding·retrieval 시간이 포함되고, answer duration에는 answer_llm 시간이 포함된다. 중첩 시간을 합산하지 않는다.

## 7. 검증

- [확인됨] `backend/tests/api/test_agent_trace.py`: 정상 RAG, 빈 검색, Tool 실패, 실제 timeout 경로, 무도구 응답, routing 실패, 동시 요청 격리, consumer close의 8개 테스트.
- [확인됨] `backend/tests/api/test_chat_auth_owner.py`: assistant metadata 저장과 기존 채팅 흐름 회귀.
- [확인됨] 합성 문자열을 질문·근거·답변·예외에 넣어 새 trace JSON에 원문이 없는지 검사한다.
- [확인됨] backend 전체 78 tests passed, 변경 파일 Ruff 통과.
- [확인됨] mypy는 기존·현재 동일한 종류의 오류 15개로 실패한다. HEAD 기준선을 임시 디렉터리에서 비교했고 새 trace 모듈·전용 테스트의 추가 오류는 없다.
- [확인 필요] 실제 모델·DB·브라우저 기반 QA와 운영 로그 수집 환경에서 확인.

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/api/test_agent_trace.py -q
```

## 8. 후속 범위

- HTTP request ID와 Agent trace 연결, DB 저장과 SSE 실패 계측
- latency 및 fallback 빈도를 동일 평가 run에서 집계
- token usage 수집, 검색 query의 개인정보 없는 관측 방식 검토
- 외부 관측 도구·파일 sink·보존 기간은 운영 필요에 따라 결정
- 다단계 실행 도입 시 step ID와 종료 이유 확장

따라서 MVP2 Step 3 전체 완료 대신 최소 graph trace 구현 완료로 기록한다.

## 9. 답변 계약 검증 trace 보강

- [확인됨] `answer_validation.started/completed/failed`를 추가했다.
  단계 시간, evidence_count, allowed_limitation_count를 기록한다.
- [확인됨] 검증 실패 error_code와 최종 fallback_reason은
  answer_schema_invalid / unknown_evidence_refs / unknown_limitation_codes로 구분한다.
- [확인됨] chain 내부 Pydantic 오류는 별도 검증 단계 진입 전에 실패할 수 있으며
  최종 fallback_reason은 answer_schema_invalid다.
- [확인됨] 답변 모델 입력의 allowed_limitations와 서버 검증 목록을 맞췄다.
  상세 범위는 `docs/work/2026-10-05-answer-limitation-contract-plan.md`를 따른다.
- [확인 필요] 실제 모델의 검증 실패율·자연어 답변 품질 개선 여부.
