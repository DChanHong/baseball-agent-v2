# Chat Evaluation

## 목적

Manual QA 실행 결과를 보관하고, 실패 또는 애매한 사례를 사람이 검토한 뒤 회귀 평가에 사용할 정식 case로 승격한다.

```text
Manual QA Run
→ Candidate
→ Human Review
→ Evaluation Case
→ Regression Evaluation
```

## 디렉터리 역할

```text
candidates/  실패·애매 사례의 검토 대기열
cases/       기대 동작이 확정된 재사용 평가셋
runs/manual/ 브라우저 기반 수동 QA 실행 결과
schemas/     각 데이터 파일의 JSON Schema
```

## 파일 규칙

- JSONL은 UTF-8 한 줄당 객체 하나를 사용한다.
- JSON run 파일은 한 번의 실행과 전체 집계를 함께 기록한다.
- `cases/`와 검토 이력이 있는 `candidates/`는 Git에 보관한다.
- `runs/`에는 비교 기준이 되는 baseline 또는 milestone 실행만 보관한다.
- candidate가 없을 때 빈 JSONL을 만들지 않는다. 첫 candidate가 발생하면 `manual_chat_qa_candidates.jsonl`을 생성한다.
- ID는 파일 안에서 유일해야 하며 한 번 사용한 ID의 의미를 바꾸지 않는다.

## 결과 분류

```text
passed     기대 Tool, 결과, 답변, UI 상태가 허용 범위에 있음
ambiguous  답변은 가능하지만 근거·표현·Tool 선택·UI 상태가 불안정함
failed     명확한 기대 동작과 다르거나 요청을 완료하지 못함
not_run    아직 실행하지 않았거나 준비 조건을 충족하지 못함
```

## 실패 유형

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

## 개인정보와 민감정보

다음을 저장하지 않는다.

```text
실제 사용자 대화 전문
user_profile_id
운영 conversation_id와 message_id
이메일 등 개인정보
Authorization header
cookie와 token
API key와 환경변수 값
```

초기 QA는 합성 질문만 사용한다. 실제 사용에서 발견한 문제를 옮길 때는 의미를 유지한 `sanitized_input`으로 재작성한다. Assistant 응답 전문은 기본적으로 저장하지 않고 `observed_behavior`로 요약한다.

## 검증

저장된 JSON과 JSONL은 `schemas/`의 대응 Schema로 검증한다. 정식 case는 `review_status=approved`인 항목만 회귀 평가 입력으로 사용한다.

저장소 루트에서 다음 명령을 실행한다.

```bash
backend/.venv/bin/python backend/scripts/validate_chat_evaluation_data.py
```
