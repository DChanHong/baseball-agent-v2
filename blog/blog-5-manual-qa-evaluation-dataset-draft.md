# [AI Agent] 구현 다음의 일: 실사용 QA를 평가 데이터셋으로 바꾸기

> 상태: 1차 smoke QA 결과 반영 초안
> 작성 원칙: QA 실행 전에는 결과 숫자와 원인을 확정하지 않는다. 실제 milestone run과 candidate 검토 결과만 근거로 사용한다.

## 개요

KBO Mate의 MVP 기능을 구현한 뒤, 다음 기능을 추가하기 전에 실제 사용 흐름을 검증하기로 했습니다.

이번 글에서는 일정, 구장, 날씨, 예매, RAG, follow-up 질문을 직접 실행하고, 그 결과를 단순 작업 메모가 아니라 다음 개선에서도 반복해서 사용할 수 있는 평가 데이터셋으로 바꾸는 과정을 정리합니다.

## 1. 기능 구현 뒤에도 남아 있던 문제

현재 KBO Mate에는 다음 Tool과 채팅 흐름이 있습니다.

```text
find_kbo_game
get_stadium_info
get_weather_context
search_ticketing_guide
search_stadium_guide
search_baseball_knowledge
SSE streaming
Tool card
selected_game 기반 compact context
```

각 기능의 구현 여부와 실제 질문이 끝까지 안정적으로 처리되는지는 다른 문제였습니다.

```text
사용자 질문
→ Tool routing
→ Tool input 추출
→ 데이터 조회 또는 검색
→ Tool card 표시
→ 최종 답변
→ 다음 질문의 context 유지
```

이 흐름 중 한 단계만 어긋나도 사용자는 전체 답변을 실패로 경험합니다.

## 2. 자동 갱신보다 실사용 QA를 먼저 선택한 이유

KBO 경기 일정 갱신은 cron을 연결하는 대신 필요할 때 수동 sync하는 방식으로 운영하기로 했습니다. 현재 단계의 사용량과 비용을 고려하면 자동화 자체보다 갱신 절차가 재현 가능하고, QA 전에 데이터 기준 시점을 확인할 수 있는지가 더 중요하다고 판단했습니다.

수동 갱신 운영을 3-1의 완료 기준으로 삼고, 다음 단계에서는 실제 질문에서 드러나는 실패를 수집하는 데 집중했습니다.

## 3. 무엇을 성공과 실패로 분류했는가

결과는 두 가지가 아니라 네 가지로 나눴습니다.

```text
passed
ambiguous
failed
not_run
```

`ambiguous`를 별도로 둔 이유는 Tool 실행에 성공했더라도 근거가 약하거나, 답변이 지나치게 확정적이거나, UI 상태가 불안정할 수 있기 때문입니다.

실패 원인도 다음 계층으로 분리했습니다.

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

## 4. QA 질문을 어떻게 구성했는가

첫 실행은 기존 MVP 수동 QA의 대표 질문 6개와 follow-up 3개로 시작합니다.

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

```text
롯데 오늘 경기 알려줘 → 어디서 해?
롯데 오늘 경기 알려줘 → 몇 시야?
롯데 오늘 경기 알려줘 → 상대가 누구야?
```

이후 질문을 30개로 확장해 정상 질문, 짧은 질문, 복수 조건, 정보 부족, 정책 질문을 함께 다룹니다.

## 5. 실행 결과와 실패 후보를 분리한 이유

모든 실패를 바로 정식 평가셋에 넣지 않았습니다.

```text
Manual QA Run
→ Candidate
→ Human Review
→ Evaluation Case
→ Regression Evaluation
```

실행 당시의 환경 문제와 반복 가능한 제품 실패를 구분하지 않으면 평가셋이 일회성 문제로 채워질 수 있습니다. 그래서 실행 결과는 run에 남기고, 검토할 사례만 candidate로 옮긴 뒤, 기대 동작이 명확한 사례만 정식 case로 승격합니다.

## 6. 대화 전문을 저장하지 않는 데이터 구조

평가 데이터의 목적은 사용자 대화를 보관하는 것이 아니라 문제를 재현하는 것입니다.

```text
data/chat/evaluation/
├── candidates/
├── cases/
├── runs/manual/
└── schemas/
```

실제 사용자 대화 전문, 사용자 식별자, 쿠키, 토큰은 저장하지 않습니다. 초기 질문은 합성 데이터로 만들고, 실제 사용에서 발견한 문제는 개인정보를 제거한 `sanitized_input`으로 다시 작성합니다.

## 7. 첫 QA에서 발견한 실패 유형

첫 smoke QA에서는 대표 질문 6개와 follow-up 3개를 실행했습니다.

```text
전체 9개
passed 4
ambiguous 3
failed 2
```

일정 조회는 정상 동작했습니다. 2026년 9월 8일 롯데 경기를 질문하자 `find_kbo_game`이 실행됐고, 경기 시간, 구장, 상대 팀, 상태가 Tool card와 최종 답변에서 일치했습니다.

직전 경기 조회 뒤 이어서 질문한 장소, 시간, 상대 팀 질문도 통과했습니다.

```text
어디서 해?
몇 시야?
상대가 누구야?
```

세 질문 모두 Tool을 다시 호출하지 않고 `selected_game` context를 사용했습니다. Compact Context를 도입한 목적이 실제 사용자 흐름에서도 동작한 사례였습니다.

반면 구장 주소 질문은 `get_stadium_info`가 올바르게 선택되고 카드도 완료됐지만, 주소 값이 `정보 없음`으로 표시됐습니다. Routing 성공과 사용자 요청 완료가 같은 의미는 아니었습니다.

고척돔 음식물 반입 질문도 비슷했습니다. `search_stadium_guide`는 실행됐지만 검색 결과는 주류, 캔, 병, PET 음료 제한을 설명했을 뿐 음식물 반입 가능 여부를 직접 뒷받침하지 못했습니다. 이 사례는 retrieval 성공 여부를 단순히 결과 개수로 판단하면 안 된다는 점을 보여줬습니다.

날씨, 예매, 야구 지식 질문은 `ambiguous`로 분류했습니다.

```text
날씨: 근거와 한계 표시는 적절했지만 구두점 조립이 어색했다.
예매: 카드에는 예매 경로가 있었지만 최종 답변은 문서를 찾았다는 안내에 머물렀다.
야구 지식: 카드에는 보크 정의가 있었지만 최종 답변이 정의를 직접 설명하지 않았다.
```

이 결과에서 다음 candidate 5개를 만들었습니다.

```text
source_limitation 1개
answer_quality 3개
rag_retrieval 1개
```

이 중 영향도가 있는 4개는 기존 evaluation case의 기대 조건에 연결했고, 경미한 구두점 문제 1개는 보류했습니다.

## 8. Evaluation Case 승격 기준

다음 조건을 기준으로 candidate를 정식 case로 승격합니다.

```text
같은 intent에서 반복적으로 발생하는가
사용자 경험이나 신뢰도에 직접 영향을 주는가
잘못 확정했을 때 위험한 답변인가
변경 후 회귀할 가능성이 높은가
기대 Tool 또는 답변 정책을 명확히 정의할 수 있는가
반복 실행할 가치가 있는가
```

## 9. 이 데이터셋을 이후 개선에 사용하는 방법

정식 evaluation case는 이후 단계의 공통 비교 기준이 됩니다.

```text
현재 routing baseline
→ LangChain adapter 비교
→ observability 필드 검증
→ hybrid search 전후 비교
→ query rewrite와 fallback 비교
→ answer policy와 citation 평가
```

같은 질문을 유지해야 변경 이후 정말 나아졌는지, 다른 기능을 깨뜨리지는 않았는지 확인할 수 있습니다.

## 10. 현재 한계와 다음 작업

첫 run을 기준으로 다음 개선 순서를 정했습니다.

```text
1. 사직구장 주소와 돔 여부 기본 데이터 점검
2. RAG Tool 최종 답변이 첫 근거를 직접 요약하도록 개선
3. 고척 음식물 반입 source와 chunk coverage 점검
4. 날씨 답변 문장 조립의 중복 구두점 수정
5. 개선 후 동일 9개 case 재실행
6. 준비된 나머지 21개 case를 다음 milestone run에서 검증
```

## 11. 정리

첫 QA에서 확인한 핵심은 Tool이 호출됐다는 사실만으로 성공을 판단할 수 없다는 점이었습니다.

```text
Tool 선택이 맞아도 데이터가 비어 있을 수 있다.
검색 결과가 있어도 질문에 필요한 근거가 아닐 수 있다.
카드에 답이 있어도 최종 자연어 답변이 사용자 질문을 직접 해결하지 않을 수 있다.
```

반대로 `selected_game`을 작게 저장한 Compact Context는 세 가지 follow-up 질문에서 의도한 대로 동작했습니다.

실패를 바로 수정하기 전에 run, candidate, case로 나누어 기록하니 다음 작업의 우선순위가 구현자의 감상이 아니라 재현 가능한 질문에서 나왔습니다. 앞으로도 기능이나 검색 설정을 변경할 때 동일 case를 다시 실행해 개선 여부와 회귀를 함께 확인할 수 있습니다.
