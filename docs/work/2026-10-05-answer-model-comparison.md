# 답변 모델 분리와 실제 비교 결과

> 2026-10-05 / 구현·비교 완료 / 기본 모델 교체 보류

## 목표와 반영한 변경

최종 답변 단계가 15초 timeout에 근접하므로 라우팅과 답변 모델을 분리해 비교한다.

- [확인됨] `Settings.openai_answer_model` / `OPENAI_ANSWER_MODEL`을 추가했다.
- [확인됨] 최종 답변 모델은 명시적 생성자 override → 답변 전용 설정 → 기존 `OPENAI_MODEL` 순서로 선택한다. 비어 있으면 기존 동작을 유지한다.
- [확인됨] `answer_llm` trace에 실제 모델과 답변 timeout을 기록한다.
- [확인됨] `backend/scripts/compare_answer_models.py`로 공개 근거 수집과 답변 비교를 분리했다. DB 수집은 read-only transaction이며 rollback한다.
- [확인됨] 기본 모델과 로컬 `.env`는 교체하지 않았다. 새 외부 라이브러리나 SaaS를 도입하지 않았다.

## 비교 조건

사용자가 승인한 운영 Supabase의 공개 RAG 자료만 읽었다. 실제 사용자 대화와 DB 쓰기는 없다.
병살, 보크, 사직 예매, 사직 주차의 검색 결과를 한 번 수집하고, 합성 빈 결과 사례를 추가했다.
다섯 질문을 모델별 3회 실행했다. 같은 bounded evidence, 입력 hash, prompt, timeout 15초를 사용했다.
실행 순서는 모델을 교차하고 두 번째 반복은 역순으로 했다. 독립적인 모델 API 호출 30회다.

이는 **답변 생성 서비스만** 비교한 실행이다. routing, embedding, retrieval, DB 저장, SSE, 브라우저 응답까지의 전체 지연은 포함하지 않는다.
근거 없는 VIP 질문은 실제 검색 실패를 주장하는 자료가 아니라 합성 빈 Tool 결과다.

## 측정 결과

| 항목 | gpt-5-mini | gpt-4.1-mini |
|---|---:|---:|
| 호출 수 | 15 | 15 |
| 답변 생성·계약 검증 완료 | 11 | 15 |
| 15초 timeout | 4 | 0 |
| 전체 시도 중앙값 | 13.551초 | 1.440초 |
| 성공한 시도만의 중앙값 | 11.823초 | 1.440초 |
| 전체 시도 최소–최대 | 6.199–15.011초 | 0.946–2.123초 |

전체 시도 중앙값은 약 89.4% 감소했고, 성공한 시도끼리 비교하면 약 87.8% 감소했다.
timeout 값은 실패가 결정되기까지 기다린 시간이며, 성공 응답 시간으로 집계하지 않는다.
양쪽의 반환된 답변에서 이번 실행의 목록 밖 limitation 오류는 관찰되지 않았다.
이것이 이전 limitation 수정의 개선율이나 전체 서비스 성공률을 입증하지는 않는다.

## 품질 점검과 결정

JSON 계약 통과와 내용의 정확성은 별도다. 임시 합성 답변을 근거와 대조해 다음 문제를 확인했다. 독립적인 사용자 검수는 아직 받지 않았다.

- 후보의 병살 설명이 ‘두 명의 주자’, ‘동시에’, ‘한 번의 공격’ 등으로 정의를 바꿨다. 근거는 ‘하나의 연속된 플레이에서 두 개의 아웃’이다.
- 후보의 보크 설명에서 투수판에서 발을 빼거나 와인드업에서 완전히 정지하지 않는 것을 일반화한 예시가 나왔다. 조건을 생략하면 오해를 만든다.
- `needs_review`를 구조화 필드에 넣어도 자연어 답변에서는 기준일·검수 필요 안내를 누락했다.
- 일부 주차 답변은 미확인 사항을 설명하면서 `fully_answerable`로 분류했다.
- 빈 결과 사례는 후보 3회 모두 확인 불가로 답했다.
- 기존 모델도 기준일 또는 검수 안내 누락이 일부 있었다. 품질 문제가 모두 해결된 기준 모델이라는 의미는 아니다.

정의 범위를 보존하고 검수 안내를 반드시 문장에 넣도록 prompt를 보강한 뒤 후보만 추가 15회 실행했다.
계약 검증 15/15, timeout 0/15, 중앙값 1.354초였지만 같은 종류의 내용 문제가 남았다.
재실험은 prompt가 달라졌으므로 최초 모델 비교와 별도 run으로 남긴다.
효과가 확인되지 않은 prompt 변경은 적용하지 않고 실험 snapshot만 보관했다.

**결정: 설정 분리와 평가 도구는 반영하고, 기본 답변 모델 교체는 보류한다.**
빠른 응답만으로 품질 통과를 선언하지 않는다. 평가 결과는 `manual_review`에 원문 없이 사례별 요약 label로 남겼다.

## 재현과 기록

backend에서 실행한다. 첫 명령은 DB 읽기·embedding API, 두 번째는 모델 API를 사용하므로 승인된 환경에서만 실행한다.

```bash
.venv/bin/python scripts/compare_answer_models.py --prepare \
  --dataset ../data/chat/evaluation/cases/answer_model_comparison_cases.json

.venv/bin/python scripts/compare_answer_models.py \
  --dataset ../data/chat/evaluation/cases/answer_model_comparison_cases.json \
  --models gpt-5-mini gpt-4.1-mini --repeats 3 --timeout 15 \
  --output /private/tmp/baseball-answer-model-run.json
```

이미 수집한 fixture를 사용하면 DB를 다시 읽지 않는다. run은 모델, 입력·dataset·prompt hash, 소요 시간, 계약 실패와 수동 검토 요약을 저장한다.
합성 답변 전문은 검토용 `/private/tmp` 파일에만 생성하며 Git에는 저장하지 않는다.
이번 frozen fixture는 기존 `chat_mvp_cases.jsonl`과 다른 답변 전용 형식이다. 기존 chat validator의 검증 대상이 아니다.

보관한 milestone:

- `data/chat/evaluation/cases/answer_model_comparison_cases.json`
- `data/chat/evaluation/runs/answer-model/2026-10-05_gpt5mini_vs_gpt41mini.json`
- `data/chat/evaluation/runs/answer-model/2026-10-05_gpt41mini_policy_refinement.json`
- `data/chat/evaluation/runs/answer-model/2026-10-05_rejected_answer_policy.md`

검증: backend 전체 96 passed. 변경 Python 파일 Ruff lint·format 및 `git diff --check` 통과.

## 다음 작업

1. 근거의 정의와 제한 안내를 기준으로 답변 품질 평가 항목을 고정한다.
2. 검수 필요 안내를 모델의 선택에 맡기는 방식과 서버가 보완하는 방식의 계약을 정한다.
3. 개선한 모델·정책 조합이 품질 기준을 통과하면 답변 전용 설정으로 적용한다.
4. 실제 브라우저 QA에서 routing부터 SSE까지 전체 지연과 fallback을 확인한다.
