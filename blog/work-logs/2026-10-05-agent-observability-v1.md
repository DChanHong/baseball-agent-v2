# Agent 최소 trace 구현 작업 기록

> 날짜: 2026-10-05
> 범위: MVP2 Step 3 첫 회차
> 커밋: 미실행

## 목표와 작업 전 상태

routing과 Tool·답변 로그는 있었지만 공통 실행 ID와 단계별 시간이 없었다.
ReAct 또는 검색 개선 전, 어느 단계가 느리고 실패했는지 확인할 기반을 만든다.

## 결정한 것

- 기존 Python logging에 JSON 이벤트를 기록한다. 외부 서비스나 DB table은 추가하지 않는다.
- trace 단위는 graph 실행 한 번이다. HTTP·DB 저장·전송 시간은 후속 범위다.
- graph state의 ID를 node 실행 안에서 ContextVar로 전달한다. 전역 mutable ID를 사용하지 않는다.
- 질문, 검색 원문, 답변과 예외 메시지를 새 trace에 기록하지 않는다.
- 모델 실패 후 fallback으로 답했다면 turn은 completed이며 답변 경로로 실패를 구분한다.
- 검색 결과 존재 여부와 LLM의 최종 answerability를 다른 필드로 남긴다.

## 구현한 것

- `backend/app/core/agent_trace.py`: scope, 단계 timing, JSON 로그
- `backend/app/agent/graph.py`: turn/route/tool/answer trace 및 중단 경로
- RAG handler 3개: embedding/retrieval 계측과 chunk ID·distance
- 답변 생성 서비스: answer_llm 호출 시간과 실패 타입
- 기존 assistant metadata: trace ID, 답변 경로, fallback 사유
- spec: `docs/spec/2026-10-05-agent-observability-spec.md`

## 확인한 결과

- backend 전체 테스트: 78 passed
- trace 전용 테스트: 8개
- 정상, 빈 검색, Tool 예외, 답변 timeout, 무도구 응답, routing 예외 검증
- 동시 요청 ID 격리와 consumer close 기록 검증
- 합성 비공개 문자열이 새 trace JSON에 포함되지 않음
- 기존 Tool SSE 이벤트 순서 및 assistant metadata 저장 회귀 검증
- 변경 파일 Ruff 통과

테스트는 fake router·embedding·retriever와 fake answer chain을 사용했다.
Timeout은 실제 `AnswerGenerationService`의 시간 제한을 짧게 설정해 검증했다.
운영 응답 속도 또는 실제 모델의 품질 개선 수치로 해석하지 않는다.

## 실행 중 발견한 점

저장소 이동으로 `.venv/bin/pytest`의 interpreter 경로가 현재 경로와 달랐다.
환경을 재설치하지 않고 `.venv/bin/python -m pytest`로 검증했다.
타입 검사 결과는 기존 코드 기준선과 별도로 비교했다. 자세한 결과는 아래 검증 메모에 남긴다.

## 다음 작업

1. 승인된 환경에서 기존 QA 질문을 재실행해 단계별 latency와 fallback 빈도를 기록한다.
2. 기존 evaluation case와 trace의 비교 필드를 정해 Step 4 반복 평가에 연결한다.
3. HTTP·DB 저장·SSE 실패를 포함할지 범위를 결정한다.
4. 실패 데이터에 따라 검색 개선 또는 제한된 multi-step으로 확장한다.

## 블로그에 살릴 포인트

- 최종 응답이 완료돼도 모델이 성공한 것은 아닐 수 있다.
- 검색 결과가 있다는 것과 질문에 답할 수 있다는 것은 다르다.
- nested 단계 시간을 합산하면 실제 latency보다 과장된다.
- 관측을 위해 사용자 대화를 복사할 필요는 없다.
- LangGraph node task에서 ContextVar를 설정·복원해 동시 요청을 구분했다.

## 검증 메모

운영·DB 접속, migration, 실제 API 호출, git commit·push는 수행하지 않았다.

- mypy: 통과하지 않음. 변경 전 HEAD의 app 파일을 임시 디렉터리에 복원해
  비교한 결과, 기존·현재 모두 동일한 종류의 오류 15개가 나왔다.
- 기존 오류는 Settings 생성, SQLAlchemy 타입, 날씨 client/handler,
  RAG schema의 Literal 목록, routing 모델 API key와 favorite_team 타입에 있다.
- 새 trace 모듈·전용 테스트에서 추가 오류는 없다. 이번 범위 밖의 기존 오류는 수정하지 않았다.
- `git diff --check`: 통과.
