# MVP2 데이터 커버리지·최종 답변 품질 개선 계획

> 상태: 진행 중
> 작성일: 2026-09-08
> 대상: MVP2 3-2 이후 데이터 커버리지, RAG 근거, 최종 답변 품질
> 선행 문서: `docs/work/2026-09-08-mvp2-3-2-manual-qa-evaluation-dataset-plan.md`

## 1. 목적

실사용 QA에서 확인된 실패를 데이터 부족, 검색 실패, 답변 생성 실패로 분리하고 순서대로 개선한다. LLM이 자연스러운 문장을 만드는 것보다 먼저 답변에 필요한 근거가 존재하는지 확인하며, 근거가 부족할 때는 부족함을 명확히 알리는 동작도 품질 기준에 포함한다.

## 2. 현재 기준선

- [확인됨] chat 평가셋에는 일정, 구장, 날씨, 예매, 구장 안내, 야구 지식, 후속 질문, 정책, 미지원 요청을 포함한 30개 case가 있다.
- [확인됨] 첫 브라우저 수동 QA는 9개 질문을 실행했고 `passed 4 / ambiguous 3 / failed 2`를 기록했다.
- [확인됨] 질문 routing에는 실제 서비스 프롬프트, OpenAI 모델, `ToolRoutingDecision` Pydantic 검증이 사용됐다.
- [확인됨] 최종 자연어 답변은 현재 `backend/app/agent/answering.py`의 결정적 템플릿으로 생성된다.
- [확인됨] 구장 가이드 normalized 문서는 9개 구장 × 5종류, 총 45개이며 embedded input도 45개다.
- [확인됨] 야구 지식 embedded input은 27개다.
- [확인됨] 위 RAG chunk 72개는 모두 `trust_level=official`이지만 `review_status=needs_review`다.
- [확인됨] 사직구장 주소는 migration SQL에 존재하지만 첫 QA의 실제 Tool 결과에서는 누락됐다.
- [추론] 사직구장 주소 실패는 원천 파일 부재보다는 로컬 DB migration 또는 seed 반영 상태 차이일 가능성이 높다. DB 상태 확인 전에는 원인을 확정하지 않는다.

## 3. 문제 분류

### 3.1 구조화 데이터 상태 차이

대상 예시:

- `사직구장 주소 알려줘`

확인할 항목:

- migration 적용 여부
- 현재 `kbo_stadiums.address`, `is_dome`, `source_url`, `as_of` 값
- seed 재실행 후 값 보존 여부

DB 조회, migration, seed 실행은 별도 사용자 확인을 받은 뒤 수행한다.

### 3.2 원천·문서 커버리지 부족

대상 예시:

- `고척돔 음식물 반입 가능해?`
- 현장 발권, 취소·환불, 예매 오픈 시각
- 구장별 예외 반입 정책

현재 문서가 질문의 핵심을 직접 뒷받침하지 않으면 관련 chunk가 검색되더라도 `answerable`로 간주하지 않는 방향으로 개선한다.

### 3.3 검색 적합도 부족

대상 예시:

- 질문과 직접 관련 없는 야구 지식 근거 동시 노출
- 음료 용기 제한 문서를 음식물 반입 답변 근거로 사용하는 경우

검색 성공 여부를 단순히 `items` 존재 여부로 판정하지 않고, 질문 핵심과 근거의 직접 관련성을 평가한다.

### 3.4 최종 답변 활용 부족

대상 예시:

- 예매 경로가 Tool card에 있지만 답변은 “문서를 찾았다”에서 끝남
- 보크 정의가 검색됐지만 답변에서 설명하지 않음

검색 결과를 문장 수나 길이 규칙으로 잘라 붙이는 중간 구현은 사용자 판단에 따라 생략한다. 검색 근거, 출처, limitation을 제한된 입력으로 구성해 LLM이 질문에 직접 답하게 하고, 기존 결정적 템플릿은 LLM 호출 또는 검증 실패 시 fallback으로만 유지한다.

## 4. 답변 가능 상태 정의

각 평가 질문은 다음 상태 중 하나로 관리한다.

| 상태 | 의미 | 기대 답변 |
|---|---|---|
| `answerable` | 필요한 근거가 있고 질문에 직접 답할 수 있음 | 근거의 핵심 사실을 직접 안내 |
| `partially_answerable` | 관련 근거는 있지만 일부 조건이 없음 | 확인된 내용과 부족한 내용을 분리 |
| `insufficient_source` | 질문 핵심을 뒷받침할 근거가 없음 | 추측하지 않고 공식 확인 경로 안내 |
| `unsupported` | 현재 Tool 또는 서비스 범위 밖 | 지원 범위와 대안 안내 |

`items`가 1개 이상이라는 이유만으로 `answerable`을 확정하지 않는다.

## 5. 평가 케이스 영역별 초기 커버리지

| 영역 | case 수 | 현재 근거 | 초기 판단 | 주요 과제 |
|---|---:|---|---|---|
| 경기 일정 | 5 | `kbo_games` | 부분 충족 | 수동 갱신 시점과 최신성 표시 |
| 구장 기본 정보 | 3 | `kbo_stadiums` | 부분 충족 | DB 반영 상태 확인 |
| 날씨 | 3 | KMA 단기 데이터 | 부분 충족 | 기준 시점·취소 비확정 표현 |
| 장기 날씨 미지원 | 1 | 없음 | 충족 | 지원 범위 설명 유지 |
| 예매 | 3 | 구장별 ticketing guide | 부분 충족 | 직접 답변, 최신성, 세부 정책 보강 |
| 구장 안내 | 4 | 구장별 guide | 부분 충족 | 질문 핵심별 직접 근거 점검 |
| 야구 지식 | 4 | 공식 규칙 기반 chunk | 부분 충족 | curated 요약 검수, 검색 노이즈 감소 |
| 후속 질문 | 4 | `selected_game` context | 충족 | 회귀 테스트 유지 |
| 답변 정책 | 1 | 날씨 limitation | 충족 | 취소 확정 금지 유지 |
| 미지원 요청 | 2 | routing policy | 충족 | Tool 오호출 방지 유지 |

이 표는 저장소 기준의 초기 판단이다. 실제 DB와 vector index 상태를 확인한 뒤 실행 단위 커버리지로 갱신한다.

## 6. 단계별 실행 계획

### Phase 1. 근거 기반 LLM 최종 답변 — 진행 중

- [x] 첫 수동 QA 실패를 candidate와 evaluation case에 연결
- [x] routing 모델과 답변 생성 모델의 책임 분리
- [x] 사용자 질문, Tool 결과, source, limitation만 답변 모델에 전달
- [x] 근거 밖 사실 생성 금지 및 prompt injection 방어 프롬프트 적용
- [x] `answerability`, 최종 답변, 사용 근거, limitation을 Pydantic schema로 검증
- [x] 알 수 없는 evidence ref를 반환하면 실패 처리
- [x] 실패 시 기존 결정적 템플릿 fallback 사용
- [x] 실제 LLM을 통한 브라우저 QA 2건 재실행

완료 조건:

- 최종 답변이 질문에 직접 답한다.
- 답변의 사실을 Tool payload의 evidence ref로 역추적할 수 있다.
- 근거가 없으면 `insufficient_source`로 분류하고 부족함을 명시한다.

### Phase 2. 구조화 데이터 동기화 확인

- [ ] 사용자 승인 후 로컬 DB의 `kbo_stadiums` 필드 상태 조회
- [ ] migration 적용 상태와 seed 동작 비교
- [ ] 주소·돔 여부·출처·기준일 누락 목록 작성
- [ ] 필요한 경우 기존 migration/seed 보완 후 Tool 재검증

완료 조건:

- 평가 대상 구장의 필수 필드가 DB와 저장소 정의에서 일치한다.
- 주소가 없을 때 Tool이 성공처럼 보이지 않고 limitation을 제공한다.

### Phase 3. 문서 커버리지와 검수 상태 개선

- [ ] 30개 case별 필수 사실과 현재 source/chunk 매핑
- [ ] `needs_review` 72개를 우선순위별 검수
- [ ] 고척 음식물 반입처럼 직접 근거가 없는 질문을 `insufficient_source`로 표시
- [ ] 공식 출처를 확보한 항목만 normalized·embedded input에 반영
- [ ] embedding/index 갱신 전 사용자 승인

우선순위:

1. 안전·취소·환불처럼 잘못 단정하면 신뢰에 영향을 주는 정보
2. 첫 QA에서 실패한 구장 주소와 음식물 반입
3. 예매 경로와 현장 발권
4. 좌석·교통·시설 세부 정보

완료 조건:

- 각 smoke 질문에 `answerable / partially_answerable / insufficient_source`가 지정된다.
- `approved` 근거와 `needs_review` 근거가 답변 정책에서 구분된다.

### Phase 4. 최종 답변 평가 자동화

우선 결정적 검증을 사용한다.

- 필수 사실 포함
- 금지 주장 부재
- Tool 결과와 수치·팀·날짜·구장 불일치 없음
- limitation 필요 시 표시
- source 또는 기준일 필요 시 표시

표현의 자연스러움처럼 결정적으로 평가하기 어려운 항목만 사람 검토 또는 보조 LLM judge 대상으로 둔다.

완료 조건:

- 30개 core case를 반복 실행할 수 있다.
- 동일 run 형식으로 변경 전후 결과를 비교할 수 있다.
- 실패가 candidate로 다시 유입된다.

## 7. 이번 회차 구현 범위

DB와 vector index를 변경하지 않고 다음을 수행한다.

1. `AnswerGenerationService`를 routing과 분리한다.
2. RAG는 상위 3개 근거만 전달하고 각 content는 최대 6,000자로 제한한다.
3. 비 RAG Tool은 검증된 Tool result 전체를 단일 evidence로 전달한다.
4. LLM 출력은 `GroundedAnswerDraft` Pydantic schema로 검증한다.
5. 생성·검증 실패 시 기존 답변 템플릿으로 fallback한다.
6. 생성 결과의 answerability와 evidence ref를 assistant message metadata에 저장한다.

검색 결과를 단순히 잘라 붙이는 중간 방식은 구현하지 않는다. 이번 범위는 실제 LLM 답변 생성 경로를 추가하되, 검색 결과 자체의 정확성이나 DB 데이터는 변경하지 않는다.

실제 브라우저 smoke 결과:

- `보크가 뭐야?`: 검색 근거로 개념과 결과를 직접 설명하고 기준일·검수 상태를 표시했다.
- `고척돔 음식물 반입 가능해?`: 음식물 직접 근거가 없음을 인식해 확답하지 않고 확인된 음료 제한만 분리해서 안내했다.
- 두 요청 모두 완료까지 약 37~42초가 걸렸다. 기능 정확성과 별개로 답변 생성 latency 최적화가 필요하다.

## 8. 검증 방법

```bash
cd backend
./.venv/bin/pytest tests/api/test_answer_generation_service.py -q
./.venv/bin/pytest tests/api -q
./.venv/bin/python scripts/validate_chat_evaluation_data.py
```

브라우저 재검증 질문:

```text
사직 예매 어디서 해?
보크가 뭐야?
고척돔 음식물 반입 가능해?
사직구장 주소 알려줘
```

## 9. 변경 중 지켜야 할 원칙

- 사용자 데이터, 인증값, 실제 대화 전문을 저장하지 않는다.
- 공식 출처라도 `needs_review` 상태이면 검수되지 않았음을 숨기지 않는다.
- 날씨만으로 경기 취소를 확정하지 않는다.
- 예매 잔여석, 가격, 오픈 시간처럼 변동 가능한 값은 확인 근거 없이 생성하지 않는다.
- DB, migration, seed, embedding/index 변경은 사용자 확인 후 실행한다.

## 10. 결정 사항과 열린 항목

### 결정 사항

- 평가셋 30개를 품질 개선의 고정 기준선으로 사용한다.
- 데이터 부족도 실패가 아니라 명시적으로 처리해야 할 답변 상태로 관리한다.
- 검색 결과를 잘라 붙이는 규칙 기반 중간 개선은 생략한다.
- Tool 성공 응답은 근거 기반 LLM 답변 생성을 사용한다.
- 기존 결정적 답변은 생성·검증 실패 시 fallback으로 유지한다.
- 초기 답변 모델은 routing과 같은 `openai_model` 설정을 사용한다.

### 사용자 확인이 필요한 후속 작업

- 로컬 DB 상태 조회 및 migration/seed 보완 실행
- RAG 문서 보강 후 embedding/vector index 갱신
- routing과 답변 생성의 모델·비용 설정 분리 여부
