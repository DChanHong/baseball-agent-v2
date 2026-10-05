# 최종 답변 limitation 계약 개선 계획과 결과

> 작성일: 2026-10-05
> 상태: 코드·합성 회귀 검증 완료, 실제 모델·운영 QA 미실행
> 선행 작업: 최소 Agent trace 구현과 실제 4개 실행 관찰

## 문제와 목표

실제 RAG 실행에서 모델 응답이 반환됐지만 허용되지 않은 limitation 때문에
기본 답변으로 전환됐다. 약 20초를 기다렸지만 모델 답변을 사용하지 못했다.
이번 범위는 허용 목록을 모델과 서버가 공유하고 실패를 구분하는 것이다.
모델·timeout·검색·streaming 변경과 latency 최적화는 별도 회차로 둔다.

## 구현 전 상태

- [확인됨] Tool의 `limitations`와 evidence가 모델 입력에 전달됐다.
- [확인됨] 서버는 Tool limitation, 전달된 evidence의 needs_review,
  metadata.limitations와 content_truncated를 모아 허용 목록을 계산했다.
- [확인됨] 계산된 전체 목록은 독립적인 모델 입력 필드로 전달되지 않았다.
- [확인됨] 출력은 자유로운 문자열 목록이며, 없는 코드를 반환하면 ValueError였다.
- [추론] 자연어 제한 설명과 metadata 코드 선택을 명확하게 구분하면 잘못된
  코드 생성을 줄일 수 있다. 실제 감소 여부는 합성 테스트로 확정할 수 없다.

## 작업 순서와 구현 결과

1. 합성 출력으로 목록 밖 코드와 자연어 코드의 검증 실패를 재현했다.
2. bounded evidence를 만든 뒤 기존 허용 규칙으로 `allowed_limitations`를 계산했다.
3. 모델 입력과 서버 검증에 동일 목록을 사용한다. 중복을 제거하고 정렬한다.
4. prompt와 출력 field description에 정확한 코드 선택·빈 목록 규칙을 명시했다.
5. schema, evidence ref, limitation 코드 오류를 안정적인 실패 코드로 구분했다.
6. 서비스·graph 회귀 테스트와 문서를 보강했다.

관련 코드:

- `backend/app/agent/answer_generation_service.py`
- `backend/app/agent/answer_schemas.py`
- `backend/app/agent/prompt_assets/answer_generation_policy.md`
- `backend/app/agent/graph.py`

`acknowledged_limitations`는 여전히 `list[str]`이고 요청별 JSON Schema enum을
생성하지 않는다. 선택 목록은 입력과 prompt로 제시하며 서버가 엄격히 검증한다.
허용되지 않은 값을 삭제하거나 다른 코드로 자동 변환하지 않는다.
추가 모델 재시도도 없다.

## 검증과 관측 계약

`answer_validation.started/completed/failed`를 추가했다.
단계 시간, 근거 수, 허용 코드 수와 실패 코드를 남기며 원문 출력은 기록하지 않는다.

| 조건 | fallback_reason / validation error_code |
|---|---|
| Pydantic schema 위반 | `answer_schema_invalid` |
| 존재하지 않는 evidence ref | `unknown_evidence_refs` |
| 목록 밖 limitation 코드 | `unknown_limitation_codes` |
| 모델 시간 제한 | 기존 `TimeoutError` 유지 |

Chain 내부에서 Pydantic 검증이 먼저 실패하면 answer_llm.failed가 남고,
별도 answer_validation 단계에 진입하지 않는다. 최종 fallback 사유는
answer_schema_invalid로 동일하게 분류한다.

검증 대상:

- Tool 코드·needs_review·metadata 코드·본문 잘림 허용
- 빈 허용 목록과 빈 선택 목록
- 새 코드, 자연어 코드와 answerability를 limitation에 넣는 오류
- 상위 3개 밖의 evidence는 허용 목록에 영향을 주지 않음
- schema 검증·evidence ref 오류·timeout 후 fallback
- trace에서 실패 종류 구분과 합성 비공개 문자열 부재
- 호출 횟수 1회 유지와 기존 SSE 완료 흐름

실제 모델의 답변 품질·누락된 limitation·지연 감소는 아직 측정하지 않았다.
검증 통과가 자연어 답변의 사실성 전체를 보장하는 것은 아니다.

검증 결과: backend 전체 92 passed, 변경 파일 Ruff lint·format 및
`git diff --check` 통과. mypy는 기존 동일한 종류의 오류 15개로 미통과다.
이번 실행은 DB와 실제 모델을 호출하지 않았다.

## 다음 실제 검증

DB·실제 API 사용 범위를 확인한 뒤 같은 합성 평가 질문으로 재실행한다.
야구 지식, needs_review 문서, 근거 없음과 본문 잘림을 포함한다.
trace ID, 단계별 시간, 최종 answer_source, fallback_reason을 비교하고,
답변에 필요한 한계가 표현됐는지는 사람이 확인한다.
결과는 개인정보 없는 evaluation run에 기록한다.
