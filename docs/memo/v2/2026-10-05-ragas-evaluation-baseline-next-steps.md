# 다음 작업: RAGAS 기반 평가 지표와 기준선 만들기

> 작성일: 2026-10-05
> 상태: 평가 지표·입력 계약 정의 완료 / reference 보강부터 진행
> 선행 구현 커밋: `2b6c5ac perf: reduce guide answer latency with scoped reasoning policy`
> 이 문서를 다음 회차의 시작점으로 사용하고, 완료한 항목과 결과 링크를 계속 갱신한다.

## 1. 현재 어디까지 진행했는가

- [확인됨] 최소 agent trace로 routing → Tool → embedding/retrieval → 답변 생성·검증을 연결했다.
- [확인됨] 모델과 서버의 limitation 허용 목록을 맞추고 실패 코드를 구분했다.
- [확인됨] 기존 gpt-5-mini를 유지하며 구장·예매 안내에만 low 추론을 적용했다. 야구 규칙과 그 밖의 Tool 답변은 medium을 유지한다.
- [확인됨] 구장 안내 합성 질문 9회 비교에서 답변 단계 중앙값은 12.251초 → 4.491초였다. 전체 화면 응답 시간의 개선율은 아니다.
- [확인됨] 검수 대상 근거를 사용하면 서버가 기준일·검수·공식 출처 재확인 안내를 붙인다.
- [확인됨] 기존 chat 평가 case와 수동 QA 기록, 고정 근거를 사용하는 답변 비교 run이 있다.
- [확인됨] 평가 전용 의존성에 `ragas==0.4.3`과 호환용 `langchain-community==0.4.1`을 고정했다. 지표 factory·입력 adapter·offline 검증과 전용 테스트를 추가했다. 실제 평가 실행과 품질 기준선 구축은 아직 미완료다.

관측과 답변 지연 개선의 첫 회차는 마무리했다. **평가 지표·입력 계약을 정의했으며, 다음은 공식 근거를 확인해 reference를 보강하는 작업이다.** 실제 baseline 점수는 아직 측정하지 않았다.

관련 기록:

- [RAGAS 평가 지표·입력 계약](../../spec/2026-10-05-ragas-evaluation-contract-spec.md)
- [RAGAS 라이브러리 도입·offline 검증](../../work/2026-10-05-ragas-library-bootstrap.md)
- [합성 입력 실제 지표 smoke: 2개 사례·8개 점수](../../work/2026-10-05-ragas-synthetic-metric-demo.md). 실제 judge API 실행 완료, 서비스 baseline은 미측정.
- [일반 채팅 API 표본 Faithfulness](../../spec/2026-10-05-online-ragas-faithfulness-spec.md): SSE 전송 후 5% 표본·일일 $0.10 예약 상한·원문 미보관으로 연결했다. 합성 통합 테스트 완료, 실제 서비스 baseline·유료 E2E 실행은 미완료.
- [MVP2 전체 계획](../../planning/002-mvp2-backend-upgrade-plan.md)
- [속도 개선과 적용 정책](../../work/2026-10-05-answer-latency-reasoning-policy.md)
- [기존 QA 데이터 계획](../../work/2026-09-08-mvp2-3-2-manual-qa-evaluation-dataset-plan.md)
- [블로그 6: 관측부터 답변 개선까지](../../../blog/blog-6-agent-observability-answer-improvement-draft.md)

## 2. 바로 다음 작업: 평가 지표 정의

RAG 평가 부분은 RAGAS의 지표와 입력 형식을 기준으로 설계한다. 다음 표는 **도입할 후보이며 아직 구현·측정한 결과가 아니다.**

| 지표 후보 | 확인할 것 | 우리 서비스에서의 목적 |
|---|---|---|
| Faithfulness | 답변의 주장이 전달된 근거로 뒷받침되는가 | 근거에 없는 예매 정책·야구 규칙 설명 탐지 |
| Response/Answer Relevancy | 질문 의도에 맞게 답했는가 | 질문과 무관한 설명, 핵심 질문 미응답 확인 |
| Context Precision | 유용한 검색 근거가 상위에 배치됐는가 | 다른 규칙이나 다른 구장 문서가 섞이는 검색 노이즈 확인 |
| Context Recall | 기대 답변에 필요한 정보가 검색 근거에 포함됐는가 | 답변에 필요한 규정·구장 안내 누락 확인 |

지표 정의의 출처:

- [Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [Response Relevancy](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)
- [Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)
- [Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)

Faithfulness는 근거와의 일치도이지 원문 자체의 정확성·최신성 보장이 아니다.
Relevancy도 사실 정확성을 평가하는 지표가 아니므로, 정답 기준과 필수·금지 주장을 따로 둔다.
Context Recall은 reference가 필요하고 Context Precision은 reference 유무에 따라 구현을 선택한다.
2026-10-05 공식 stable 문서의 `metrics.collections` API를 기준으로
`Faithfulness`, `AnswerRelevancy`, reference 기반 `ContextPrecision`, `ContextRecall`을 설계에 선택했다.
필수 입력·근거 분리·적용 제외·별도 서비스 검사는 위 평가 계약에 정의했다.
패키지 버전을 고정한 뒤 설치 버전의 import·인자·결과 형태를 검증한다.

RAGAS 지표와 별도로 서비스 평가도 유지한다:

- 기대 Tool 선택과 args 일치 여부
- 기대 chunk/topic 적중 여부(top1/top3 등)
- 필수 사실·금지 주장, 기준일·검수 안내, 근거 없을 때의 확인 불가 응답
- 계약 검증 실패, timeout, fallback 비율
- 단계별 지연과 실제 end-to-end 지연, 토큰 사용량
- SSE 완료와 화면 로딩 종료

RAGAS 점수만으로 전체 Agent 성공 여부를 판정하지 않는다.
경기 조회·날씨·후속 context 직접 응답은 각각의 계약으로 평가하고, 세 RAG Tool에는 검색·답변 지표를 적용한다.

## 3. 먼저 준비할 평가 데이터와 실행 계약

초기 데이터는 기존 합성 QA 질문을 활용한다. 기존 9개 smoke 질문 중 RAG 사례를 먼저 선정하고,
규칙·구장 안내·예매의 정상 사례와 근거 부족·검수 대상 사례를 포함한다.
전체 30개 chat case를 모두 같은 RAGAS metric으로 평가하지 않는다.

평가 입력 후보:

```text
case_id
user_input                 합성 질문
response                   실제 평가 대상 답변
retrieved_contexts         생성기에 실제 전달한 근거 본문과 필요한 출처 metadata
reference                  검수된 기대 답변 또는 필수 사실
retrieved/reference IDs    chunk 또는 topic 적중률 계산용
```

기존 chat case의 expected Tool·answer policy를 RAG 평가 reference로 자동 간주하지 않는다.
공식 근거를 확인하고 기대 사실을 검수해 보강한다. needs_review 자료나 모델 생성 답변을 검수 없이 정답으로 사용하지 않는다.

검색 결과 전체와 생성기에 전달한 bounded evidence는 구분한다. 답변 Faithfulness는 실제 전달 근거를 기준으로 평가한다.
검색 순위 평가는 별도로 원래 검색 목록을 사용한다. 서버가 덧붙인 검수 안내도 평가 입력에 필요한 metadata를 포함하거나 별도 정책 검사로 분리해 잘못 감점하지 않도록 한다.

빈 근거의 확인 불가 답변은 별도 정책 사례로 점검한다. 계산할 수 없는 metric을 임의로 0이나 1로 채우지 않고 적용 제외 사유를 기록한다.

실행마다 다음을 고정·기록한다:

```text
dataset 버전/hash, source 기준일
RAGAS 버전과 metric 변형
생성 모델과 도구별 reasoning 설정, prompt hash
평가 모델·embedding 모델·평가 prompt/설정
retrieval top_k·filter·근거 제한
metric별 점수·평가 오류·적용 제외 사유
생성 지연·토큰 및 평가 비용/시간의 구분
```

초기 점수를 보기 전에 임의의 합격선부터 정하지 않는다.
소규모 baseline과 수동 내용 점검을 함께 수행하고, 중요한 실패 사례를 기준으로 회귀 판정 규칙을 확정한다.

운영 Supabase 읽기나 실제 생성·평가 API 실행은 범위와 비용을 확인한 뒤 진행한다.
이미 승인된 범위가 있으면 그 범위 안에서 이어간다. 실제 사용자 대화, 인증값과 API key는 저장하지 않는다.
합성 질문·공개 근거만 사용하고 평가에 필요한 합성 답변의 보관 범위도 먼저 정한다.

## 4. 순차 진행 체크리스트

위에서 아래 순서로 진행한다. 각 단계 완료 시 체크하고 결과 파일·run·커밋을 이 메모에 연결한다.
검색 개선 단계는 baseline의 실패 유형을 보고 필요한 항목만 선택한다.

- [x] 최소 관측 로그, limitation 계약 수정, 답변 생성 지연 실험과 도구별 설정 적용 완료 (`2b6c5ac`).
- [x] RAGAS 평가 지표·필수 입력·적용 대상·서비스 별도 검사 항목을 [문서로 확정했다](../../spec/2026-10-05-ragas-evaluation-contract-spec.md). 코드·공식 문서 대조 완료, 실행 측정은 미완료.
- [ ] **다음 시작: 기존 평가 데이터에서 RAG 사례를 선정하고 검수된 reference·필수 사실·기대 근거를 보강한다.** Smoke의 예매·음식물 반입·보크 3개를 후보로 선정했으며 reference 검수는 아직 하지 않았다.
- [ ] RAGAS 버전을 고정하고 평가용 의존성·judge/embedding 설정·실행 및 비용 범위를 정한다. **의존성 설치·버전 고정·실제 API import 검증은 완료**했으며 judge 설정·실행 비용 범위는 남아 있다.
- [ ] 기존 실행 결과를 평가 입력으로 변환하고 metric별 결과·오류·적용 제외를 저장하는 최소 평가 runner를 만든다. **입력 adapter·지표 factory·scoring 함수·offline 검증 CLI는 완료**했으며 실제 입력 수집·run manifest·점수 저장 연결은 남아 있다.
- [ ] 기존 9개 smoke 질문을 실제 routing·검색·답변·SSE 경로로 재실행한다. RAG 사례에는 RAGAS 평가를 연결한다.
- [ ] 자동 점수와 수동 검토를 대조하고 실패를 routing / retrieval / grounding / policy / runtime으로 분류한다.
- [ ] 야구 규칙 조건 혼동, 검수 안내 누락, 근거 없음 응답을 회귀 사례로 확정한다.
- [ ] 나머지 chat case로 QA를 확장하고 세 RAG Tool별 검색·답변 baseline을 고정한다. 대표 RAG 질문 15~30개는 커버리지를 보고 별도로 구성한다.
- [ ] 중요한 실패의 회귀 기준을 확정하고 baseline 결과와 평가 작업의 블로그 초안을 남긴다.
- [ ] 검색 baseline이 보여준 실패를 기준으로 hybrid search를 비교한다. 필요 없으면 보류 사유를 기록한다.
- [ ] 짧은 질문·follow-up 실패가 있으면 query rewrite / retrieval fallback을 같은 평가셋으로 비교한다.
- [ ] 검색 순위 문제에 필요하면 reranking을 비교하고 정확도·지연·비용으로 도입을 결정한다.
- [ ] 답변과 source/citation 연결, 최신성·needs_review 표시를 보강하고 회귀 평가한다.
- [ ] Prompt Injection·Tool Abuse·데이터 유출·source trust 보안 평가를 보강한다.
- [ ] 복합 질문의 단일 Tool 한계가 확인되면 제한된 multi-step/ReAct를 도입한다. max step·timeout·retry·종료 사유를 함께 정의한다.
- [ ] 실제 token streaming·첫 토큰 시간·CI smoke/regression 자동화를 필요에 맞게 보강한다.
- [ ] 각 회차의 구현·비교 결과·남은 과제를 이 메모와 MVP2 계획에 갱신하고, 커밋 요청 시 검증 후 기록한다.

## 2026-10-06 실행 업데이트

실제 로컬 API·DB·유료 온라인 평가, 화면 smoke 9개와 초기 RAG 3개 baseline을 실행했다.
[실행·검수·실패 결과](../../work/2026-10-06-ragas-service-baseline-e2e.md)를 확인한다.
고척 음식물 근거 부족과 보크 timeout은 미해결 품질 개선 항목이다.
reference 검수 주체는 agent이며 사람 검수 완료로 해석하지 않는다.
