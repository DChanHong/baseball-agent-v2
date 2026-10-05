# 기존 모델의 답변 지연 개선과 적용 정책

> 2026-10-05 / 실제 API 비교·코드 적용 완료
> 개선 범위: 구장·예매 안내 답변 생성. 야구 규칙 추론량과 라우팅은 유지한다.

## 원인과 실험

입력 metadata 축소만으로 지연 감소를 확인하지 못해 실제 토큰 사용량을 계측했다.
기존 모델 gpt-5-mini를 유지하고 `medium`과 `low`를 같은 공개 frozen evidence로 교차 실행했다.
모델 반환의 raw message에서 숫자 토큰 counter만 읽는다. 답변·추론 전문은 trace에 기록하지 않는다.
공식 문서에서도 낮은 reasoning effort의 지연/품질 tradeoff를 설명하므로 실제 답변 내용까지 점검했다.

첫 비교는 질문 5개 × 설정 2개 × 3회 = 30회다.
답변 시간 중앙값은 medium 10.003초, low 4.832초였고 reasoning token 중앙값은 1,024 → 256이었다.
이후 서버 검수 안내와 정의 답변 지침을 보강해 같은 크기의 별도 비교를 했다.
추가로 실제 적용하는 도구별 정책을 15회 실행했다. 이번 회차의 모델 API 호출은 총 75회이며 DB 접속은 없다.

## 적용한 변경

- `OPENAI_ANSWER_REASONING_EFFORT` 기본값은 low다. 기존 모델 gpt-5-mini를 유지한다.
- 기본 설정의 빠른 추론은 `search_ticketing_guide`, `search_stadium_guide`에만 사용한다.
- 야구 지식, 경기 조회 및 그 밖의 Tool 답변에는 medium을 유지한다. 라우팅 설정은 바꾸지 않는다.
- GPT-5 계열이 아닌 답변 모델에는 reasoning parameter를 보내지 않는다.
- 생성자에서 명시적으로 전달하는 reasoning override는 통제 실험용이며 기본 도구별 정책을 우회한다.
- raw structured output을 받아 기존 schema/ref/limitation 검증을 유지하고 토큰 counter를 추출한다.
- trace에 effective reasoning effort, input 문자 수, input/output/total/reasoning/cache 토큰 수를 남긴다.
- 실제 사용한 needs_review 근거에 대해 서버가 기준일과 검수·공식 출처 재확인 문장을 붙인다.
- 검증하지 않은 새 limitation은 여전히 거부한다. 서버가 직접 추가하는 안내만 needs_review 코드로 기록한다.
- 최종 안내를 붙인 뒤 길이 등 schema를 다시 검증한다. 범위를 초과하면 기존 계약 실패 처리로 간다.

본문 생성은 모델이 담당한다. 기준일은 실제 사용한 evidence의 유효한 ISO 날짜에서만 가져온다.
근거가 없는 답변이나 사용하지 않은 문서에 검수 안내를 임의로 붙이지 않는다.

## 실제 속도 결과

최종 prompt와 동일 근거를 사용하는 통제 비교 중 **구장 안내 3개 질문 × 3회 = 9회**를 비교한다.
야구 규칙을 제외한 적용 범위의 결과다. 전체 시도 중앙값에는 timeout까지의 대기를 포함한다.

| 답변 생성 단계 | medium | low |
|---|---:|---:|
| 호출 수 | 9 | 9 |
| 생성·계약 검증 완료 | 7 | 9 |
| 15초 timeout | 2 | 0 |
| 중앙값 | 12.251초 | 4.491초 |
| reasoning 토큰 중앙값¹ | 960 | 256 |

¹ usage가 반환된 성공 호출 기준. timeout은 토큰 수를 0으로 해석하지 않는다.

중앙값은 약 **63.3% 감소**했다. 설정 순서를 교차하고 두 번째 반복은 역순으로 실행했다.
Prompt cache와 외부 API 변동이 있으므로 이 작은 표본의 감소율을 운영 전체 수치로 일반화하지 않는다.

실제 기본 도구별 정책을 다시 15회 실행한 결과:

- 안내 답변 9회: low, 9/9 완료, timeout 0, 중앙값 4.275초.
- 야구 지식 6회: medium, 5/6 완료, timeout 1, 중앙값 10.888초.
- 전체 답변 생성 시도 중앙값: 5.648초. 이 수치는 혼합 정책 확인 run의 값이며 별도 통제 비교의 baseline과 합치지 않는다.

**야구 규칙 답변의 지연과 timeout은 아직 남아 있다.** 전체 HTTP·DB 저장·SSE·브라우저 표시까지의 속도 개선율은 측정하지 않았다.

## 정확도 때문에 유지한 경계

일괄 low 실험의 보크 답변에서 와인드업과 세트 포지션의 정지 조건을 섞어 설명한 사례가 있었다.
따라서 일괄 low는 적용하지 않았다. 야구 규칙은 기존 추론량을 유지한다.
빠른 안내 답변에서는 예매처, 실시간 잔여석·주차 대수 미확인, 빈 근거의 확인 불가를 점검했다.
적용 정책 재실행의 안내 답변 9회는 이 핵심 기준을 만족했고 검수 대상 답변에는 서버 안내가 포함됐다.
내용 점검은 assistant가 수행했으며 사용자/독립 검수자의 승인이나 전체 정확도 보장과 구분한다.
기존 medium도 모든 예시 표현이 완벽하다는 의미는 아니다. 중복 기준일 안내나 장황한 문장은 추가 개선 여지가 있다.

## 검증과 기록

Backend 전체 113 passed, 변경 Python 파일 Ruff lint·format과 git diff --check 통과.
토큰 counter의 숫자 allowlist, raw 출력 비노출, parser 오류, 검수 안내와 길이 계약,
도구별 실제 체인 선택, 비지원 모델 호환성을 검사했다.

주요 파일:

- `backend/app/agent/answer_generation_service.py`
- `backend/app/core/config.py`
- `backend/app/agent/prompt_assets/answer_generation_policy.md`
- `backend/scripts/compare_answer_models.py`
- `data/chat/evaluation/runs/answer-model/2026-10-05_gpt5mini_reasoning_comparison.json`
- `data/chat/evaluation/runs/answer-model/2026-10-05_gpt5mini_final_latency_comparison.json`
- `data/chat/evaluation/runs/answer-model/2026-10-05_gpt5mini_applied_tool_policy.json`

Prompt snapshot은 run의 SHA-256과 대조해 보관했다. 사용자 대화와 API key는 저장하지 않았다.
설정 로드로 현재 로컬 모델 gpt-5-mini 및 answer effort low를 확인했다. 운영 서버에 배포하거나 사용자의 실행 프로세스를 재시작하지는 않았다.
실행 중 백엔드가 변경을 reload하지 않으면 재시작해야 새 설정이 반영된다.

backend에서 DB 접속 없이 비교를 재현한다:

```bash
.venv/bin/python scripts/compare_answer_models.py \
  --dataset ../data/chat/evaluation/cases/answer_model_comparison_cases.json \
  --models gpt-5-mini --reasoning-efforts medium low --repeats 3 --timeout 15 \
  --output /private/tmp/baseball-reasoning-comparison.json
```

실제 기본 정책을 확인하려면 `--reasoning-efforts`를 생략한다.
`OPENAI_ANSWER_REASONING_EFFORT=medium`으로 설정하면 안내 답변도 기존 추론량으로 되돌릴 수 있다.

공식 문서:

- [GPT-5의 reasoning 설정과 기본값](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools)
- [Reasoning effort의 속도·품질 tradeoff](https://developers.openai.com/api/docs/guides/reasoning)
