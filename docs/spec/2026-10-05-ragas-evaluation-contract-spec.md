# RAGAS 평가 지표와 입력 계약

> 작성일: 2026-10-05
> 상태: 평가 설계 확정 / runner·reference 검수·baseline 측정 미완료
> 범위: MVP2 3.5 Evaluation Baseline의 첫 단계
> 시작 메모: [다음 작업](../memo/v2/2026-10-05-ragas-evaluation-baseline-next-steps.md)
> 후속 구현: [라이브러리 도입·offline 검증](../work/2026-10-05-ragas-library-bootstrap.md). 아래 현재 구현은 계약 정의 당시 snapshot이며, 이후 의존성·adapter 구현 범위는 후속 기록을 따른다.
> 운영 연결: [일반 채팅 API 표본 Faithfulness](2026-10-05-online-ragas-faithfulness-spec.md). 네 지표 baseline 측정 완료와는 구분한다.

## 1. 목적

검색 순위, 생성기에 전달된 근거, 답변 품질을 구분해 현재 세 RAG Tool의 기준선을 만든다. RAGAS 점수를 Agent 전체 성공률로 바꾸지 않는다. 이 문서의 2장은 현재 구현이며, 3장 이후는 앞으로 구현할 평가 계약이다. 설계 확정은 측정 완료를 뜻하지 않는다.

## 2. 현재 구현과 재사용 한계

- [확인됨] RAG Tool은 `search_baseball_knowledge`, `search_stadium_guide`, `search_ticketing_guide`다. 각 handler가 embedding → 검색 → items·limitations 반환을 수행한다.
- [확인됨] [검색 설정](../../backend/app/domains/baseball/tool/rag_config.py)은 `text-embedding-3-small`, 기본 top_k 5·최대 10이다. relevance threshold는 야구 지식 0.82, 구장·예매 0.65다. 실제 적용 filter와 요청 top_k도 run에 기록해야 한다.
- [확인됨] [답변 입력 구성](../../backend/app/agent/answer_generation_service.py)은 검색 items의 상위 3개만 사용하고 각 content를 6,000자로 자른다. 일부 indexing metadata는 제거하며 domain metadata·출처·기준일·검수 상태는 유지한다. items가 비면 `kind=tool_result` evidence를 만든다. 이것을 검색 문서 1개로 세면 안 된다.
- [확인됨] 같은 서비스가 사용된 evidence의 `review_status=needs_review`를 확인해 답변에 검수·공식 출처 재확인 안내를 붙인다. 유효한 `as_of`가 있으면 기준일도 붙인다.
- [확인됨] [기본 설정](../../backend/app/core/config.py)과 답변 서비스에서 기본 답변 모델은 `gpt-5-mini`, 구장·예매의 기본 reasoning은 low이고 다른 Tool은 medium을 사용한다. 명시적 설정으로 달라질 수 있으므로 run은 실제 유효 설정을 기록한다.
- [확인됨] [trace](../../backend/app/core/agent_trace.py)는 근거 본문과 답변을 저장하지 않는다. [graph](../../backend/app/agent/graph.py)의 완료는 DB 저장·SSE 완료·화면 로딩 종료를 보장하지 않는다.
- [확인됨] [기존 비교 스크립트](../../backend/scripts/compare_answer_models.py)는 고정 근거 답변 비교다. 저장 run에는 답변 길이·hash·계약 결과 등이 있지만 답변 전문은 임시 review 파일에만 쓴다. 기존 요약 run만으로 RAGAS 답변 지표를 복원할 수 없다.
- [확인됨] [backend 의존성](../../backend/pyproject.toml)에 RAGAS가 없다. RAGAS 평가 runner와 검수된 RAG reference dataset은 이번 작업에서 구현·생성하지 않았다.

## 3. 적용 대상과 초기 사례

정상 RAG 답변에는 아래 네 지표를 사용한다. 기대 Tool과 실제 Tool이 다르면 routing 실패를 먼저 기록한다. 그 답변의 진단 점수는 별도 집계하며 정상 Tool baseline에 섞지 않는다.

기존 [9개 smoke run](../../data/chat/evaluation/runs/manual/2026-09-08_manual-qa-v1.json) 중 RAG 입력 후보는 다음 3개다. **후보 선정이며 reference 검수 완료가 아니다.**

| case_id | 질문 | 기대 Tool |
|---|---|---|
| chat_ticket_001 | 사직 예매 어디서 해? | search_ticketing_guide |
| chat_guide_001 | 고척돔 음식물 반입 가능해? | search_stadium_guide |
| chat_knowledge_001 | 보크가 뭐야? | search_baseball_knowledge |

나머지 6개는 경기·구장 기본 정보·날씨·selected_game follow-up 계약으로 평가한다. 9개 전체의 routing·runtime·SSE 결과는 유지한다.

추가 커버리지는 야구 규칙 조건 혼동, 근거 없음, 부분 근거, needs_review 근거 사용이다. [고정 근거 fixture](../../data/chat/evaluation/cases/answer_model_comparison_cases.json)는 합성 빈 근거와 공개 근거 입력을 재사용할 수 있지만 기대 답변을 제공하는 정답셋은 아니다. needs_review 자료나 모델 답변을 자동으로 정답으로 승격하지 않는다.

## 4. 지표 정의와 API 선택

2026-10-05에 확인한 공식 stable 문서는 `ragas.metrics.collections`와 `ascore(...)` → `result.value`를 안내한다. 아래 이름은 이 문서의 설계 기준이다. **패키지 버전은 아직 고정하지 않았으며**, 설치 버전의 import·필수 인자·결과 형태를 offline fixture로 검증한 뒤 runner API를 확정한다. legacy API와 점수를 혼용하지 않는다.

| 기록 이름 / collections 클래스 | 필수 입력 | 평가할 것 | judge 자원 |
|---|---|---|---|
| faithfulness / Faithfulness | user_input, response, retrieved_contexts | 답변 주장이 실제 전달 근거로 뒷받침되는 비율 | LLM |
| answer_relevancy / AnswerRelevancy | user_input, response | 질문 의도와 답변의 관련성 | LLM + embedding |
| context_precision / ContextPrecision | user_input, reference, retrieved_contexts | 검수 reference에 유용한 근거가 상위에 있는가 | LLM |
| context_recall / ContextRecall | user_input, reference, retrieved_contexts | reference의 사실이 검색 근거에 포함되는 비율 | LLM |

Faithfulness는 근거 자체의 최신성·사실 정확성을 보장하지 않는다. [공식 정의](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

Answer Relevancy는 사실 정확성과 별개다. 질문 재생성 개수 `strictness`는 초기 3으로 고정한다. cosine 기반 점수는 음수가 가능하므로 임의로 0~1로 clamp하지 않는다. [공식 정의](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)

Context Precision은 검수 reference가 있는 변형을 기본으로 선택한다. reference가 없는 `ContextUtilization`은 생성 답변 기준의 진단 후보이며 기본 precision을 대체하지 않는다. reference 미검수 사례는 precision·recall을 제외한다. [공식 정의와 변형](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)

Context Recall은 reference 사실의 근거 포함 여부를 평가한다. 검색 결과 수나 ID 적중률과 별개다. [공식 정의](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)

## 5. 입력 계약과 근거 구분

아래 필드는 runner용 저장 계약이며 아직 JSON Schema로 구현되지 않았다.

| 필드 | 의미 / 수집 위치 |
|---|---|
| case_id, case_version, user_input | 기존 case와 연결한 합성 질문·버전 |
| expected_tool, observed_tool, tool_input | 기대·실제 Tool과 args; routing 별도 검사 |
| response, response_origin | 최종 사용자 답변과 llm/fallback/template 등 생성 경로 |
| model_response, source_notice | 서버 후처리 직전 모델 답변과 서버가 추가한 안내; 문자열 추정으로 분리하지 않음 |
| retrieval_items | Tool이 반환한 원래 순위의 본문·chunk/document/topic ID·distance·출처 metadata |
| generation_evidence | 실제 GroundedAnswerRequest의 evidence payload·E ref·순서·잘림 상태 |
| used_evidence_refs, answerability, limitations | 모델 사용 ref와 서버 허용 limitation, 응답 계약 결과 |
| reference, reference_review | 검수된 기대 사실을 문장으로 작성; 검수 상태·주체·일자·공식 출처·출처 기준일 |
| required_facts, forbidden_claims | 지표와 별도로 검사할 필수 사실·금지 주장 |
| expected_chunk_ids / expected_topic_ids | 사람이 검수한 기대 근거; 어떤 ID 기준을 썼는지 명시 |

`reference`에는 검색으로 확인할 domain 사실만 넣는다. 검수 안내나 답변 어투는 별도 정책 기대값으로 둔다. 공식 출처 확인일과 자료 기준일을 구분하고, `needs_review` 원문만으로 reference를 approved 처리하지 않는다.

지표별 adapter는 다음 입력을 만든다.

- **Faithfulness:** `model_response`와 실제 `generation_evidence`의 공개 근거를 사용한다. content와 생성기에 전달한 domain metadata를 결정적인 직렬화 규칙으로 구성한다. 삭제된 metadata, 잘리기 전 본문, 사용되지 않은 검색 결과를 추가하지 않는다. 직렬화 규칙 버전/hash를 기록한다.
- **Answer Relevancy:** 동일한 `model_response`를 사용해 서버가 붙인 안내에 의한 차이를 줄인다. 사용자에게 보인 최종 `response`의 정책·사실 점검은 별도로 한다.
- **Context Precision / Recall:** 원래 `retrieval_items` 순서와 본문·domain metadata를 사용한다. 적용 top_k·filter 이후 Tool 반환 목록을 기준으로 한다. precision이 원래 순위를 유지하도록 정렬·중복 제거를 임의로 수행하지 않는다.
- **선택 진단:** bounded evidence의 recall도 보고 싶으면 `context_recall_generation`으로 별도 기록한다. 검색 recall과 합치지 않고 절단으로 생긴 정보 누락을 구분한다.

현재 서비스의 `execute()`는 서버 안내가 붙은 draft를 반환한다. 따라서 후처리 전 답변·안내·실제 request를 보존하는 합성 평가 전용 수집 경로가 필요하다. 기존 trace에 운영 질문·답변 전문 로깅을 추가하는 방식은 사용하지 않는다. 과거 최종 답변만 있으면 문자열을 잘라 model_response를 추정하지 않고 `missing_model_response`로 제외한다.

## 6. 적용 제외와 평가 오류

metric 결과는 `status=scored|excluded|error`, `value=number|null`, `reason_code`, `duration_ms`를 갖는다. excluded/error에는 점수를 넣지 않는다. NaN·무한대·judge의 무효 출력은 error다. 수치 0인 정상 점수와 제외를 구분한다.

| 상황 | 처리 |
|---|---|
| 기대 RAG Tool이 아닌 사례 | 네 지표 excluded: non_rag_case |
| 빈 검색 근거를 의도한 정책 사례 | 네 지표 excluded: empty_evidence_policy_case; 확인 불가·금지 주장 검사 |
| 정상 reference 사례인데 실제 검색이 비었음 | 근거 지표 excluded: empty_retrieval; retrieval 실패·ID hit 실패는 별도 유지 |
| reference 없음 / 미검수 | precision·recall excluded: missing_reference / reference_not_approved |
| 모델 답변 없음·fallback·template | 답변 지표 excluded: missing_model_response / non_llm_response; runtime·최종 정책 검사는 유지 |
| 검색은 성공했지만 생성 실패 | reference가 있으면 검색 지표는 실행; 답변 지표만 제외 |
| timeout·judge API 실패 | error: judge_timeout / judge_api_error; 재시도 횟수·비용 포함 |
| 계산 가능한 주장이 없어 값이 무효 | error: undefined_score; 0 또는 1로 대체하지 않음 |

부분 근거 답변은 reference를 답변에 맞춰 줄이지 않는다. 누락은 recall과 필수 사실 검사로 남기고, 확인 불가 표현이 적절한지는 정책 검사로 판단한다.

## 7. 서비스 별도 검사

| 검사 | 판정 / 분모 |
|---|---|
| routing·args | 기대 Tool 일치, 명시된 filter·날짜·구장 등 값 검사; 전체 실행 사례 |
| chunk/topic hit@1·hit@3 | 검수 기대 ID 집합과 상위 k 교집합이 있는가; 기대 ID가 있는 정상 검색 사례 |
| 필수 사실·금지 주장 | 단순 키워드만으로 조건·예외를 검수 완료로 보지 않음; 최초 baseline은 사람 내용 점검 병행 |
| 검수·기준일 안내 | 사용된 ref의 needs_review·유효한 as_of를 기준으로 최종 response 검사 |
| 근거 부족 | unsupported 정책 확정 금지·확인 불가 표현·answerability 확인 |
| 계약·runtime | schema/ref/limitation 오류, timeout, fallback 각각 집계; 실행 시도 전체 |
| 지연·토큰 | 단계별·graph·HTTP/SSE·화면 완료 시간을 분리; 중첩 단계 합산 금지 |
| SSE·UI | 완료 이벤트 수신, Tool card 종결, loading 해제; 실제 E2E 실행만 판정 |

기대 ID가 없으면 hit 지표도 excluded다. 검색이 실제로 비었고 기대 ID가 있으면 hit는 false다. top_k가 3보다 작으면 실제 반환된 상위 목록을 사용하고 길이를 함께 기록한다.

실패 그룹은 `routing / retrieval / grounding / policy / runtime`을 사용한다. 기존 chat failure label을 덮어쓰지 않고 함께 기록한다. SSE/UI 실패는 runtime 그룹과 `ui_sse` label을 병기한다. judge 오류는 서비스 runtime 오류와 분리한다.

## 8. 재현성과 보관 계약

run manifest에 dataset version·파일 SHA256·case 목록, source 기준일/검수일, 코드 revision·dirty 상태, 실제 생성 모델·reasoning·prompt hash, 검색 embedding·top_k·threshold·filter, evidence 제한·adapter hash를 기록한다.

평가 측에는 RAGAS 정확한 버전·metric 클래스/변형, judge·평가 embedding 모델, 평가 prompt·언어·설정/hash, strictness·timeout·retry·동시성·반복 횟수를 기록한다. 한국어 judge 결과는 최초 수동 검토와 대조한다. 모델과 prompt는 아직 선정·검증되지 않았다.

생성과 평가 각각의 시간·token·비용을 분리한다. 제공되지 않은 token·비용 값은 null과 사유를 기록한다. 단가 기준일과 retry 비용을 포함해 비용을 계산하며, 계산 불가능한 값을 0으로 채우지 않는다.

보관은 [기존 데이터 정책](../../data/chat/evaluation/README.md)을 따른다. 이번 설계에서는 합성 답변 전문·실제 평가 입력은 `/private/tmp`의 임시 파일에서 평가·검토하고 Git에는 넣지 않는다. milestone run에는 case ID·입력 hash·점수·오류·제외 사유·설정·수동 검토 요약만 남긴다. 이 방식은 과거 답변 전문의 재평가가 불가능하므로 비교하려면 동일 case를 다시 생성해야 한다. 영구 전문 보관이 필요하면 별도로 보관 범위를 합의한다.

향후 파일 위치는 `data/chat/evaluation/cases/rag_baseline_cases.jsonl`, `schemas/rag_baseline_case.schema.json`, `runs/ragas/<run_id>.json`로 계획한다. 아직 파일을 만들거나 reference 승인 상태를 변경하지 않았다.

## 9. 집계와 완료 조건

Tool·metric별로 scored/excluded/error 수와 적용 대상 수, 유효 점수 평균·중앙값을 함께 보고한다. 정상 사례·정책 사례·routing 실패·fallback은 분리한다. 작은 표본의 평균 하나로 합격선을 정하지 않는다. 심각한 금지 주장이나 안내 누락은 높은 RAGAS 점수로 상쇄하지 않는다.

첫 baseline 완료 조건은 검수 reference, 고정 버전/설정, 실제 검색·생성 입력 수집, metric별 결과/제외/오류, 수동 내용 점검, 9개 smoke의 SSE/UI 확인이다. 현재 완료한 것은 지표·입력·적용 대상·별도 검사 계약 정의다.

다음 순서는 후보 3개의 공식 근거 확인과 reference 보강 → 의존성·judge 설정 고정 → offline adapter/runner 검증 → 승인된 범위의 실제 baseline 실행이다. DB 접속은 저장소 규칙에 따라 사용자 확인이 필요하다. 실제 생성·judge API 실행의 사례 수·반복·재시도·비용 상한은 실행 전 정한다. 이번 회차에는 DB·유료 API·commit·push를 실행하지 않았다.
