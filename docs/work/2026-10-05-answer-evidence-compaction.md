# 기존 모델을 유지한 답변 입력 축소

> 2026-10-05 / 코드 반영·실제 비교 완료 / latency 개선은 확인하지 못함

## 반영한 동작

- [확인됨] 최종 답변 RAG metadata에서 `audience`, `language`, `topic_id`, `knowledge_type`, `search_keywords`, `example_questions`를 제외한다.
- [확인됨] 본문, evidence 수·순서·ref, 기존 6000자 제한, 출처, 기준일, trust/review 상태는 유지한다.
- [확인됨] metadata의 제한사항, 요약, 원문 페이지, 시즌, 최신 여부, 티켓 URL, 지하철 정보 및 알 수 없는 도메인 필드는 유지한다. 원본 Tool 결과를 수정하지 않는다.
- [확인됨] 모델, prompt, timeout, 검색 경로는 바꾸지 않았다. `.env`도 교체하지 않았다.

수정은 `backend/app/agent/answer_generation_service.py`의 `_compact_rag_metadata`에서 한다.
검색 단계에서 쓰는 힌트를 답변 입력에서 제외하는 좁은 범위의 변경이다.
본문을 재요약하거나 관련성이 낮아 보이는 검색 문서를 자동으로 버리지 않는다.

## 실험

기존 공개 fixture의 다섯 합성 질문을 각각 3회 실행했다. 실제 모델은 양쪽 모두 `gpt-5-mini`다.
같은 prompt와 15초 timeout을 사용하고 축소 전후를 교차 실행했다. 총 30회 모델 API 호출이며 DB를 다시 읽거나 쓰지 않았다.
평가 스크립트에서만 metadata helper를 원본 보존/축소 버전으로 바꿔 대조한다.
run의 `model` 필드에는 비교군 label을, `actual_model`에는 실제 호출 모델을 기록했다.

| 질문 | 변경 전 입력 문자 | 변경 후 입력 문자 | 감소 |
|---|---:|---:|---:|
| 병살 | 2,156 | 1,953 | 9.4% |
| 보크 | 16,581 | 15,932 | 3.9% |
| 사직 예매 | 1,550 | 1,534 | 1.0% |
| 사직 주차 | 1,674 | 1,432 | 14.5% |
| 근거 없음 | 278 | 278 | 0% |

문자 수는 request JSON 기준으로 실제 토큰 수나 API 비용 감소율과 같지 않다.

| 답변 단계 결과 | 변경 전 | 변경 후 |
|---|---:|---:|
| 실행 횟수 | 15 | 15 |
| 생성·계약 검증 완료 | 12 | 14 |
| timeout | 3 | 1 |
| 전체 시도 중앙값 | 11.886초 | 12.042초 |
| 성공한 시도만 중앙값 | 11.445초 | 11.738초 |

전체 시도 중앙값은 약 1.3% 늘었다. **속도 개선을 달성했다고 볼 수 없다.**
timeout은 이번 작은 표본에서 줄었지만 반복적으로 재현되는 안정성 개선인지 확정하지 않는다.
입력이 동일한 ‘근거 없음’ 대조군도 시간 차이가 컸다. 입력 크기 외에 생성·외부 API 지연 변동이 있음을 보여준다.
routing, retrieval, DB 저장, SSE 및 브라우저를 포함한 end-to-end 측정은 아니다.

## 정확도와 검증

입력에 대한 회귀 테스트는 본문과 출처·제한 계약, 도메인 metadata, 세 evidence와 잘림 상태의 보존을 확인한다.
backend 전체 98 passed, 변경 Python 파일 Ruff lint·format과 `git diff --check`를 통과했다.

생성된 합성 답변은 assistant가 근거와 대조했다. 사용자나 독립 검수자의 품질 승인과 구분한다.
병살의 핵심 정의, 예매처, 주차 정보의 미확인 사항, 근거 없는 질문에 대한 확인 불가 응답은 유지됐다.
다만 축소 후 병살 2회차에는 기준일만 남고 검수 필요 안내가 빠졌으며,
보크 1회차의 예시 문장은 동작 중단·완료 조건을 혼동하기 쉬운 표현이었다.
원본 쪽에도 검수 안내 누락이 있었다. **정확도가 개선됐거나 완전히 보장된다고 주장하지 않는다.**
입력은 보존돼도 모델의 생성 결과가 항상 동일하지 않다는 한계가 남는다.

결정: 안전한 입력 정리 범위는 반영한다. latency 개선이나 품질 해결로 분류하지 않는다.
다음 회차는 실제 사용량의 input/output/reasoning 토큰과 단계 시간을 관찰해 생성 지연의 원인을 더 좁히고,
정의 질문의 불필요한 예시와 검수 안내 누락에 대한 답변 계약을 검증하는 순서로 한다.
reasoning 설정 조정은 정확도에 영향을 줄 수 있으므로 별도 비교 없이 적용하지 않는다.

## 재현

backend에서 실행한다. 기존 fixture를 사용하므로 DB 접속은 없고 모델 API를 호출한다.

```bash
.venv/bin/python scripts/compare_answer_models.py \
  --dataset ../data/chat/evaluation/cases/answer_model_comparison_cases.json \
  --models gpt-5-mini --compare-metadata --repeats 3 --timeout 15 \
  --output /private/tmp/baseball-metadata-run.json \
  --review-output /private/tmp/baseball-metadata-review.json
```

milestone: `data/chat/evaluation/runs/answer-model/2026-10-05_gpt5mini_metadata_comparison.json`.
실제 사용자 대화와 답변 전문은 저장소에 저장하지 않는다. 입력 보존 확인과 정성 검토 요약만 run에 남긴다.
