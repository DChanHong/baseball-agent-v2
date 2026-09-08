# MVP2 3-2 실사용 QA와 평가 데이터셋 작업 기획서

> 상태: 초기 구축 완료 — 지속 운영
> 작성일: 2026-09-08
> 대상 단계: `docs/planning/002-mvp2-backend-upgrade-plan.md`의 3.2
> 목적: 실제 서비스 사용 방식으로 QA를 수행하고, 발견한 실패와 애매한 사례를 반복 가능한 평가 데이터로 축적한다.

## 1. 배경

MVP2 3-1의 KBO 일정 갱신은 cron 또는 외부 스케줄러를 연결하지 않고 수동으로 운영한다.

확정된 운영 방식:

```text
필요한 season_year/month 수동 sync
또는 오늘 경기 수동 sync
→ 갱신된 DB를 기준으로 실사용 QA 진행
```

cron 작업은 비용 문제로 현재 범위에서 제외하고 향후 운영 개선 후보로 남긴다. 이 기준으로 3-1은 완료 처리하고 3-2 실사용 QA와 실패 케이스 수집을 시작한다.

현재 MVP는 Tool 기반 채팅, SSE, Tool card, compact conversation context를 구현했지만 실제 서비스처럼 다양한 질문을 충분히 입력하며 검증한 상태는 아니다. 3-2에서는 기능을 바로 고치기보다 먼저 실패를 재현 가능한 데이터로 남긴다.

## 2. 목표

이번 작업의 목표는 다음과 같다.

1. 실제 사용 흐름을 반영한 질문으로 채팅 기능을 수동 검증한다.
2. 각 결과를 `passed`, `ambiguous`, `failed`로 분류한다.
3. 실패가 발생한 계층과 원인을 일관된 라벨로 기록한다.
4. 실패와 애매한 사례를 사람이 검토할 수 있는 candidate로 축적한다.
5. 반복성과 영향도가 높은 candidate를 정식 evaluation case로 승격한다.
6. 이후 Tool routing, RAG, prompt, answer policy 개선 전후를 같은 질문으로 비교할 수 있게 한다.
7. QA 과정과 판단을 작업 로그에 누적하고, 실제 결과가 모인 뒤 별도 블로그 글로 재구성한다.

## 3. 비목표

이번 단계에서는 다음 작업을 하지 않는다.

```text
QA 중 발견한 문제를 즉시 모두 수정
운영 사용자 대화 전문 수집
사용자 대화를 이용한 자동 학습
운영용 observability dashboard 구축
LangSmith 또는 OpenTelemetry 선도입
평가 데이터 없이 prompt나 retrieval 설정 변경
cron 또는 유료 스케줄러 연결
```

문제 수정은 candidate 분류와 우선순위 판단 이후 별도 작업으로 진행한다.

## 4. 핵심 원칙

### 4.1 실행 기록과 평가셋을 분리한다

```text
Manual QA Run
→ Candidate
→ Human Review
→ Evaluation Case
→ Regression Evaluation
```

- `run`: 특정 시점에 수행한 QA 실행 결과다.
- `candidate`: 실패 또는 애매한 사례 중 검토할 가치가 있는 항목이다.
- `case`: 기대 동작이 명확하고 반복 실행할 가치가 있어 정식 평가셋으로 승격한 항목이다.

### 4.2 실패를 바로 정식 평가셋에 넣지 않는다

일회성 환경 오류, 데이터 준비 부족, 기대 동작이 아직 합의되지 않은 사례가 섞일 수 있다. 먼저 candidate로 남기고 사람이 검토한 뒤 승격한다.

### 4.3 대화 보관이 아니라 재현이 목적이다

실제 사용자 대화 전문이나 사용자 식별 정보를 저장하지 않는다. 평가에 필요한 최소 입력과 관찰 결과만 남긴다.

### 4.4 합성 질문을 기본으로 사용한다

초기 QA는 작성자가 준비한 합성 질문으로 실행한다. 실제 사용자 경험에서 발견한 문제를 후보로 옮겨야 할 때는 의미를 유지한 채 개인정보와 식별 정보를 제거한 `sanitized_input`으로 재작성한다.

## 5. 데이터 저장 구조

새 채팅 평가 데이터는 다음 구조로 관리한다.

```text
data/chat/
└── evaluation/
    ├── README.md
    ├── candidates/
    │   └── manual_chat_qa_candidates.jsonl
    ├── cases/
    │   └── chat_mvp_cases.jsonl
    ├── runs/
    │   └── manual/
    │       └── <timestamp>_manual-qa-v1.json
    └── schemas/
        ├── manual_chat_qa_run.schema.json
        ├── manual_chat_qa_candidate.schema.json
        └── chat_mvp_case.schema.json
```

### 5.1 Git 보관 기준

```text
evaluation/cases     항상 보관
evaluation/candidates 검토 이력이 필요한 항목 보관
evaluation/runs       baseline 또는 milestone 실행만 보관
```

로컬 확인을 위한 모든 반복 실행 결과를 Git에 계속 누적하지 않는다. 비교 기준이 되거나 블로그와 의사결정의 근거가 되는 run만 남긴다.

## 6. 데이터 계약

### 6.1 Manual QA run

한 번의 QA 실행과 집계를 JSON 파일 하나로 저장한다.

예시:

```json
{
  "schema_version": 1,
  "run_id": "manual_qa_20260908_v1",
  "executed_at": "2026-09-08T20:00:00+09:00",
  "environment": "local",
  "question_set_version": "mvp2_manual_qa_v1",
  "summary": {
    "total": 9,
    "passed": 0,
    "ambiguous": 0,
    "failed": 0,
    "not_run": 9
  },
  "results": [
    {
      "scenario_id": "qa_game_001",
      "category": "game_schedule",
      "sanitized_input": "오늘 롯데 경기 있어?",
      "expected_tool": "find_kbo_game",
      "observed_tool": null,
      "result": "not_run",
      "failure_labels": [],
      "notes": null
    }
  ]
}
```

### 6.2 Candidate

실패 또는 애매한 결과 중 검토 가치가 있는 사례를 JSONL 한 줄로 저장한다.

예시:

```json
{
  "schema_version": 1,
  "candidate_id": "qa_candidate_001",
  "source_run_id": "manual_qa_20260908_v1",
  "scenario_id": "qa_weather_003",
  "sanitized_input": "오늘 사직 경기 비 오면 취소야?",
  "result": "ambiguous",
  "failure_type": "answer_policy",
  "expected_behavior": "공식 경기 상태 없이 취소를 확정하지 않는다.",
  "observed_behavior": "날씨 정보만으로 취소 가능성을 강하게 표현했다.",
  "suspected_layer": "answer_generation",
  "severity": "high",
  "review_status": "needs_review",
  "promotion_decision": null,
  "notes": "공식 공지 연동 전에도 답변 한계를 표시해야 한다."
}
```

Candidate의 `review_status`는 다음 값을 사용한다.

```text
needs_review
promoted
rejected
deferred
```

### 6.3 Evaluation case

정식 case는 입력뿐 아니라 기대 동작을 재실행 가능한 형태로 명시한다.

최소 필드:

```text
schema_version
case_id
category
input
context
expected.is_in_scope
expected.should_call_tool
expected.tool_name
expected.tool_input
expected.answer_policy
expected.required_sources
expected.forbidden_claims
tags
source_candidate_id
```

Tool별 세부 필드가 다르면 공통 필드에 무리하게 맞추지 않고 `expected` 내부를 도메인별로 확장한다.

## 7. 결과와 실패 분류

### 7.1 실행 결과

```text
passed     기대 Tool, 결과, 답변, UI 상태가 모두 허용 범위에 있음
ambiguous  답변은 가능하지만 근거, 표현, Tool 선택 또는 UI 상태가 불안정함
failed     명확한 기대 동작과 다르거나 요청을 완료하지 못함
not_run    환경 또는 준비 문제로 아직 실행하지 않음
```

### 7.2 실패 유형

```text
tool_routing
tool_input
structured_data_freshness
rag_retrieval
rag_grounding
answer_quality
answer_policy
source_limitation
ui_sse
security_policy
runtime_error
```

결과와 실패 유형은 분리한다. 예를 들어 Tool 선택은 맞지만 근거가 약한 답변은 `ambiguous`와 `rag_grounding`으로 기록할 수 있다.

### 7.3 심각도

```text
low       표현이나 편의성 문제
medium    답변 품질 또는 재시도 경험에 영향을 줌
high      잘못된 확정 답변, 정책 위반, 핵심 기능 실패
critical  개인정보·비밀값 노출 또는 명백한 보안 문제
```

## 8. 저장 금지 데이터

다음 데이터는 QA 파일, 작업 로그, 블로그 어디에도 원문으로 저장하지 않는다.

```text
실제 사용자 대화 전문
user_profile_id
운영 conversation_id와 message_id
이메일 등 개인정보
Authorization header
cookie와 token
API key와 환경변수 값
외부 API 응답 원문에 포함된 민감정보
```

Assistant 응답 전문도 기본적으로 저장하지 않는다. `observed_behavior`로 요약하고, 정확한 문구가 재현에 반드시 필요할 때만 합성 QA 결과의 짧은 발췌를 남긴다.

## 9. QA 질문 구성

### 9.1 1차 smoke QA

기존 MVP1 수동 QA 문서의 대표 질문 6개와 follow-up 3개로 시작한다.

대표 질문:

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

Follow-up:

```text
롯데 오늘 경기 알려줘 → 어디서 해?
롯데 오늘 경기 알려줘 → 몇 시야?
롯데 오늘 경기 알려줘 → 상대가 누구야?
```

1차 목표는 제품 품질 결론을 내리는 것이 아니라 저장 형식, 분류 라벨, 실행 절차를 검증하는 것이다.

### 9.2 2차 대표 질문 확장

30개 안팎으로 확장한다.

```text
경기 일정/상태                 5
구장 기본 정보                 3
날씨                           4
예매 안내                      3
구장 가이드 RAG                4
야구 지식 RAG                  4
context 기반 follow-up         4
오류·정보 부족·정책 질문       3
```

각 영역에는 다음 변형을 포함한다.

```text
명시적인 정상 질문
짧거나 주어가 생략된 질문
복수 조건이 포함된 질문
현재 데이터로 답할 수 없는 질문
여러 Tool이 필요해 보이는 질문
확정적으로 답하면 위험한 질문
```

### 9.3 3차 실패 중심 보강

1차와 2차에서 발견된 중요 실패를 표현만 바꿔 다시 검증한다.

```text
오늘 사직 경기 취소야?
비 오는데 오늘 롯데 경기 하는 거 맞아?
사직 비 많이 오면 경기 안 하지?
```

동일 intent가 여러 표현에서 반복해 실패하면 evaluation case 승격 우선순위를 높인다.

## 10. 수동 QA 확인 항목

각 시나리오에서 다음을 확인한다.

```text
기대 Tool로 routing되는가
Tool input이 질문 의도와 일치하는가
Tool card가 running에서 completed 또는 failed로 갱신되는가
Tool 결과와 assistant 답변이 충돌하지 않는가
RAG 답변이 검색 근거 범위를 벗어나지 않는가
정보가 부족하면 limitation을 표시하는가
오류가 발생해도 user message와 재시도 경로가 유지되는가
follow-up에서 selected_game context가 유지되는가
SSE가 중간에 끊기거나 중복 렌더링되지 않는가
공식 상태 없이 경기 취소를 확정하지 않는가
```

초기 QA는 브라우저 기반 end-to-end 실행을 기본으로 한다. 정식 evaluation case로 승격한 뒤에는 가능한 항목부터 평가 스크립트로 반복 실행한다.

## 11. Candidate 승격 기준

다음 조건 중 하나 이상을 만족하고 기대 동작을 명확히 정의할 수 있으면 정식 evaluation case로 승격한다.

```text
같은 intent에서 반복적으로 발생함
사용자 경험이나 서비스 신뢰도에 직접 영향을 줌
경기 취소, 예매, 환불처럼 잘못 확정하면 위험함
prompt, routing, retrieval 변경 후 회귀 가능성이 높음
기대 Tool 또는 기대 답변 정책을 명확히 적을 수 있음
수정 후 자동 또는 반자동으로 반복 실행할 가치가 있음
```

재현할 수 없는 일회성 오류는 `deferred`, 평가 가치가 없는 사례는 사유를 남기고 `rejected`로 처리한다.

## 12. 블로그와 작업 로그 계획

### 12.1 역할 분리

```text
data/chat/evaluation  재현 가능한 실행 결과와 평가 데이터
blog/work-logs        회차별 작업과 판단 기록
blog/blog-5           여러 QA 회차를 재구성한 공개용 글
```

데이터 파일을 블로그 원고처럼 쓰거나 작업 로그를 평가 데이터 대신 사용하지 않는다.

### 12.2 회차별 작업 로그

`blog/work-log-template.md`를 바탕으로 다음 위치에 회차별 로그를 만든다.

```text
blog/work-logs/2026-09-08-mvp2-manual-qa-v1.md
blog/work-logs/<date>-mvp2-manual-qa-v<n>.md
```

기존 템플릿에는 QA 작업에서 선택적으로 사용할 수 있는 다음 항목을 추가한다.

```md
## QA / 평가 기록

- run_id
- 실행 환경
- 질문 세트 버전
- 전체 질문 수
- passed / ambiguous / failed / not_run
- candidate 생성 수
- evaluation case 승격 수

## 발견한 실패 유형

- failure_type
- 관련 scenario_id
- 기대 동작
- 실제 동작
- 추정 원인
- 재현 여부

## 데이터셋 변경

- 추가한 candidate
- 승격한 evaluation case
- 보류하거나 폐기한 candidate
- 변경 사유

## 다음 실행에서 검증할 가설
```

### 12.3 공개용 블로그 초안

`blog/blog-4-agent-context-langgraph-draft.md`의 서술 흐름을 참고하되 3-2 내용은 별도 글로 작성한다.

예정 파일:

```text
blog/blog-5-manual-qa-evaluation-dataset-draft.md
```

예정 제목:

```text
[AI Agent] 구현 다음의 일: 실사용 QA를 평가 데이터셋으로 바꾸기
```

예정 목차:

```text
개요
1. 기능 구현 뒤에도 남아 있던 문제
2. 자동 갱신보다 실사용 QA를 먼저 선택한 이유
3. 무엇을 성공과 실패로 분류했는가
4. QA 질문을 어떻게 구성했는가
5. 실행 결과와 실패 후보를 분리한 이유
6. 대화 전문을 저장하지 않는 데이터 구조
7. 첫 QA에서 발견한 실패 유형
8. Evaluation Case 승격 기준
9. 이 데이터셋을 이후 개선에 사용하는 방법
10. 현재 한계와 다음 작업
11. 정리
```

QA 결과가 나오기 전에는 숫자나 결론을 미리 작성하지 않는다. 먼저 목차와 기록 위치만 준비하고, 2~3회 실행에서 반복된 문제와 실제 판단을 근거로 완성한다.

블로그에 포함할 데이터:

```text
전체 질문 수
passed / ambiguous / failed 집계
실패 유형별 개수
개인정보를 제거한 대표 질문
기대 동작과 실제 동작의 차이
다음 개선 우선순위를 정한 근거
```

블로그에 포함하지 않을 데이터:

```text
실제 사용자 대화 전문
사용자 식별자
응답과 실행 로그 전체 덤프
비밀값 또는 인증 정보
근거 없이 추정한 실패 원인
```

## 13. 실행 단계

### Phase 1. 골격 준비

- [x] `data/chat/evaluation/` 디렉터리를 만든다.
- [x] 데이터 관리 원칙을 `README.md`에 기록한다.
- [x] run, candidate, evaluation case JSON Schema를 만든다.
- [x] 30개 chat evaluation case를 정의한다.
- [x] 1차 smoke QA 질문 세트를 run 파일에 준비한다.
- [x] 데이터 정합성 검증 스크립트를 추가한다.
- [x] `blog/work-log-template.md`에 QA 선택 섹션을 추가한다.
- [x] 첫 회차 작업 로그를 만든다.

### Phase 2. 1차 smoke QA

- [x] 로컬 Supabase 포트와 backend, frontend 실행 상태를 확인한다.
- [x] 오늘 경기 데이터가 필요한 시나리오를 위해 수동 sync 필요 여부를 확인한다.
- [x] 대표 질문 6개를 실행한다.
- [x] follow-up 3개를 실행한다.
- [x] 각 결과를 분류하고 run 파일에 기록한다.
- [x] 실패와 애매 사례를 candidate로 옮긴다.
- [x] 저장 필드와 라벨이 충분한지 검토한다.

### Phase 3. 대표 질문 확장

- [ ] 질문을 약 30개로 확장한다.
- [ ] 정상, 짧은 질문, 복수 조건, 정보 부족, 정책 질문을 포함한다.
- [ ] 두 번째 milestone run을 저장한다.
- [ ] 반복되는 실패 유형을 집계한다.

### Phase 4. Evaluation case 승격

- [x] 1차 candidate를 `promoted`, `rejected`, `deferred`로 검토한다.
- [x] 기대 동작이 명확한 4개 사례를 기존 `chat_mvp_cases.jsonl` case에 연결한다.
- [ ] 기존 Tool별 evaluation case와 중복 여부를 확인한다.
- [ ] 이후 평가 스크립트가 사용할 공통 필드와 도메인별 필드를 정리한다.

### Phase 5. 결과 정리

- [ ] QA 결과와 실패 유형 집계를 작업 로그에 남긴다.
- [ ] 다음 개선 우선순위를 정한다.
- [ ] `blog-5` 초안에 실제 결과와 대표 사례를 반영한다.
- [ ] 3-3 LangChain/LangGraph 검토와 3-4 Observability에 전달할 요구사항을 정리한다.

## 14. 실행 전 승인 지점

문서, JSON Schema, 합성 QA 데이터 파일 생성은 이 기획에 따라 진행한다.

다음 작업은 저장소 규칙에 따라 실행 전에 별도 사용자 확인을 받는다.

```text
DB 조회
KBO 일정 수동 sync
migration, seed, reset
Hosted 또는 local Supabase 데이터 변경
git commit과 push
```

## 15. 완료 조건

3-2의 초기 구축은 다음 조건을 만족하면 완료한다. 이후 run과 candidate 수집은 개선 작업마다 반복한다.

- [x] 최소 30개의 대표 질문이 정의되어 있다.
- [x] 브라우저 기반 end-to-end baseline QA run이 저장되어 있다.
- [x] 모든 실행 결과가 `passed`, `ambiguous`, `failed`, `not_run` 중 하나로 분류되어 있다.
- [x] 실패와 애매 사례가 일관된 `failure_type`으로 분류되어 있다.
- [x] 검토할 가치가 있는 사례가 candidate JSONL에 남아 있다.
- [x] 영향도가 높은 candidate가 정식 evaluation case에 연결되어 있다.
- [x] 실제 사용자 대화 전문과 개인정보가 데이터 파일에 포함되지 않았다.
- [x] 동일 case를 이후 routing, RAG, prompt 개선 평가에서 재사용할 수 있다.
- [x] 회차별 작업 로그에 결과와 의사결정이 기록되어 있다.
- [x] 블로그 초안에 사용할 집계와 대표 사례가 준비되어 있다.
- [x] 다음 개선 단계의 우선순위가 실패 데이터에 근거해 정리되어 있다.

## 16. 첫 실행 순서

```text
1. data/chat/evaluation 골격과 schema 생성
2. work-log-template에 QA 선택 섹션 추가
3. 기존 대표 질문 6개와 follow-up 3개로 최초 run 준비
4. DB 또는 수동 sync가 필요한지 확인 후 사용자 승인 요청
5. 브라우저 기반 smoke QA 실행
6. run과 candidate 기록
7. 저장 구조와 라벨 검토
8. 질문 세트를 30개로 확장
```

## 17. 현재 검증 결과

2026-09-08 기준:

```text
chat evaluation case: 30개, ID 중복 없음
manual smoke run: 1개, 9개 scenario 실행 완료
결과: passed 4 / ambiguous 3 / failed 2 / not_run 0
candidate: 5개, promoted 4 / deferred 1
run summary와 result count 일치
Pydantic 기반 데이터 정합성 검사와 전용 회귀 테스트 통과
backend 전체 테스트 50개 통과
frontend lint와 typecheck 통과
로컬 frontend 로그인과 실제 채팅 메시지 전송 확인
Tool card 완료 상태와 selected_game follow-up 3개 확인
```

검증 명령:

```bash
backend/.venv/bin/python backend/scripts/validate_chat_evaluation_data.py

cd backend
./.venv/bin/ruff check scripts/validate_chat_evaluation_data.py tests/api/test_chat_evaluation_data.py
./.venv/bin/mypy --explicit-package-bases scripts/validate_chat_evaluation_data.py tests/api/test_chat_evaluation_data.py
./.venv/bin/pytest -q

cd ../frontend
pnpm lint
pnpm typecheck
```
