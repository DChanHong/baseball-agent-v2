# [AI Agent] RAG 데이터를 운영하기: 전체 재임베딩에서 증분 갱신으로

> 상태: Phase 5 운영 반영과 검증 완료
> 기준 spec: `docs/spec/2026-09-10-stadium-guide-incremental-sync-spec.md`
> 구현 범위: 공식 출처 수집, 변경 분류, 검수, 증분 임베딩, 로컬 평가, 운영 승격과 롤백

## 개요

KBO Mate의 구장 안내는 공식 출처를 정리한 문서를 임베딩하고 Supabase
pgvector에서 검색하는 RAG 데이터다. 첫 구현은 전체 입력을 임베딩한 뒤
`document_id`와 `chunk_id`를 기준으로 upsert했다. 데이터가 작을 때
임베딩 흐름을 검증하기에는 충분했지만, 실제 운영에서는 다음 질문에 답하기
어려웠다.

```text
처음 추가된 문서인가, 기존 문서의 변경인가?
본문은 같고 임베딩 설정만 달라졌는가?
출처에서 정보가 사라진 것인가, 수집에 실패한 것인가?
새 문서에 문제가 생기면 기존 정상 문서로 돌아갈 수 있는가?
```

upsert는 같은 key의 row를 저장하는 방법이다. 무엇을 만들고, 고치고,
비활성화할지 판단하는 운영 정책까지 대신하지는 않는다. 이번 작업에서는
구장 안내 RAG를 신규·변경·삭제 후보로 분류하고, 사람이 승인한 문서만
증분 임베딩하는 반자동 파이프라인으로 바꿨다.

## 1. 실사용 QA에서 시작된 문제

출발점은 다음 질문이었다.

```text
고척돔 음식물 반입 가능해?
```

기존 고척 반입 문서는 캔, 병, PET와 주류 제한을 설명했지만 외부 음식물
반입 가능 여부를 직접 뒷받침하지 못했다. 부족한 문서 하나를 수동으로
수정하고 전체 데이터를 다시 임베딩할 수도 있었지만, 같은 방식은 정보가
바뀔 때마다 반복 비용과 운영 위험을 만든다.

그래서 문제를 다음과 같이 다시 정의했다.

```text
부족한 문서 하나를 어떻게 추가할까?
↓
공식 정보가 계속 바뀌는 상황에서 RAG 데이터를 어떻게 안전하게 갱신할까?
```

## 2. 파일이 있다고 검색되는 것은 아니었다

작업 전 저장소에는 9개 구장의 구장 안내가 있었다.

```text
normalized 문서: 45개
embedded input: 45개 chunk
공식 출처 registry: 55개
```

하지만 로컬 DB의 `rag_documents`와 `rag_chunks`에는 사직구장 문서가
각각 5개만 있었다.

```text
저장소의 embedding 입력: 45개
로컬 DB의 실제 검색 chunk: 5개
```

이 차이를 확인한 뒤부터 데이터 상태를 세 단계로 나눠 보게 됐다.

1. normalized 문서가 저장소에 존재하는가?
2. embedding 입력이 생성됐는가?
3. DB에서 활성 검색 데이터로 제공되는가?

RAG 품질을 확인하려면 파일 개수보다 실제 vector index와 활성 revision을
봐야 한다.

## 3. 변경을 저장하기 전에 분류한다

증분 갱신의 핵심은 DB 쓰기보다 앞에 있는 분류 단계다.

| 분류 | 조건 | 처리 |
|---|---|---|
| `CREATE` | 활성 논리 문서가 없음 | 신규 revision 후보 생성 |
| `UPDATE` | 활성 문서와 content hash가 다름 | 변경 revision 후보 생성 |
| `UNCHANGED` | 본문과 임베딩 설정이 같음 | 임베딩과 DB 쓰기 생략 |
| `DELETE_CANDIDATE` | 정상 수집에서 기존 정보 소실이 반복됨 | 검수 후 비활성화 후보 생성 |
| `MANUAL_REQUIRED` | 수집·추출·정규화를 신뢰하기 어려움 | 사람이 직접 확인 |
| `RE_EMBED` | 본문은 같지만 임베딩 계약이 바뀜 | 해당 문서 재임베딩 |

이번 작업에서는 기존 `text-embedding-3-small`, 1536차원을 유지했기
때문에 `RE_EMBED`는 실행하지 않았다.

## 4. 완전 자동화 대신 터미널 기반 반자동을 택했다

파이프라인은 등록된 공식 출처만 수집한다. LLM에 웹 검색을 맡기거나,
LLM이 만든 문서를 곧바로 서비스에 넣지 않는다.

```text
공식 출처 수집
→ raw snapshot과 hash 저장
→ 출처별 parser로 본문 추출
→ LLM normalized 후보 생성
→ CREATE·UPDATE·UNCHANGED 등으로 분류
→ 사람이 문서 단위로 검수
→ 승인
→ 로컬 임베딩과 검색 평가
→ 운영 승격
```

cron, 관리자 화면, 신규 URL 자동 발견은 범위에서 제외했다. 운영자가
터미널에서 직접 실행하지만 실행 이력, 멱등성, 평가 차단과 롤백에 필요한
정보는 남긴다. 자동화의 범위를 넓히기 전에 데이터 경계와 승인 기준을 먼저
안정시키려는 선택이었다.

## 5. revision으로 기존 데이터를 보호한다

새 후보를 검수하는 동안에는 현재 서비스 중인 문서를 유지한다.

```text
현재 활성 revision 유지
→ 새 revision 후보 생성
→ 검수와 승인
→ 로컬 적용과 평가
→ 새 revision 활성화
→ 이전 revision 비활성화
```

날짜가 포함된 문서 ID만 사용하던 구조도 논리 문서와 revision으로 나눴다.

```text
logical_document_id: GOCHEOK_stadium_food_guide
revision_id: GOCHEOK_stadium_food_guide_r0001
chunk_id: GOCHEOK_stadium_food_guide_r0001_chunk_000
```

하나의 논리 문서에는 활성 revision이 하나만 존재한다. 이전 revision과
embedding은 롤백을 위해 보존하고 일반 검색에서는 제외한다. 활성 revision
교체는 문서와 chunk 생성, 이전 revision 비활성화를 하나의 transaction으로
처리한다.

## 6. 삭제는 두 번 확인하고 승인한다

공식 페이지에서 문장이 보이지 않는다는 이유만으로 데이터를 삭제하지
않는다.

```text
HTTP 오류
빈 페이지
로그인 화면
접근 차단
JavaScript 렌더링 실패
페이지 개편으로 인한 selector 실패
```

이런 상태는 정보 삭제가 아니라 수집 실패다. 정상 수집 결과에서 같은
정보의 소실이 두 번 연속 확인될 때만 `DELETE_CANDIDATE`를 만든다.
이 후보도 사람이 승인해야 현재 revision을 비활성화한다. raw snapshot과
revision 이력은 물리 삭제하지 않는다.

## 7. 공통 정책과 구장별 정책을 함께 검색한다

KBO SAFE 캠페인처럼 전체 구장에 적용되는 내용을 구장마다 복사하면 정책이
바뀔 때 중복 수정이 생긴다. 공통 정책은 `stadium_id=null`인 하나의
문서로 관리한다.

```text
KBO_common_stadium_bag_policy
→ KBO 전체 구장의 공통 반입·안전 기준

GOCHEOK_stadium_bag_policy
→ 고척스카이돔의 추가 제한과 예외
```

검색기는 해당 구장의 문서와 공통 문서를 함께 조회하되, 구장별 정책을
먼저 반환한다. 서로 충돌하는 내용은 자동 병합하지 않고 검수 대상으로
남긴다.

## 8. 질문의 의미에 맞게 문서 유형을 확장했다

기존 반입 문서 하나에 음식물, 음료 용기와 주류 제한을 모두 넣으면 질문의
의도와 검색 결과가 어긋날 수 있다. 기존 5개 유형에 다음 3개를 추가했다.

| 유형 | 담당 범위 |
|---|---|
| `stadium_food_guide` | 외부 음식 반입, 취식, 구장 내 식음 매장 |
| `stadium_entry_guide` | 게이트, 입장 시간, 티켓 확인, 재입장, 입장 동선 |
| `stadium_accessibility_guide` | 휠체어석, 장애인 주차, 엘리베이터, 접근 가능한 출입구 |

캔·병·PET·주류 제한은 `stadium_bag_policy`에 유지했다. 모든 구장에
8개 유형을 강제로 만들지 않고 공식 근거가 있는 문서만 생성한다.

## 9. Phase 1: revision 기반과 관리 테이블

첫 단계에서는 수집기보다 안전한 교체 기반을 먼저 만들었다.

```text
rag_documents에 logical_document_id와 revision_number 추가
활성 여부와 활성화·비활성화 시점 추가
기존 문서를 위한 legacy_unreviewed 상태 추가
논리 문서별 활성 revision 하나만 허용
수집 실행, 출처 확인, 변경 후보, 배포 이력 테이블 추가
활성·승인 revision만 검색하도록 retriever 변경
stadium_id가 null인 공통 문서 검색 지원
신규 문서 유형의 routing schema와 Tool 설명 추가
```

기존 사직 문서 5개는 서비스를 중단하지 않도록 legacy 활성 revision으로
전환했다.

```text
로컬 migration: 완료
관리 테이블: 4개
legacy 활성 revision: 5개
중복 활성 revision: 0개
공통 문서 검색 transaction: 통과
후보 쓰기와 rollback: 통과
Supabase schema lint: 오류 없음
백엔드 API 테스트: 59개 통과
```

관련 커밋은 `9a02068 feat: add stadium guide revision foundation`이다.

## 10. Phase 2: 공식 출처 수집과 후보 생성

두 번째 단계에서는 source registry를 기준으로 수집하고 후보를 만드는
흐름을 구현했다.

```text
sources.json 검증
→ 일반 HTTP 수집
→ 출처별 parser
→ 필요할 때만 브라우저 adapter
→ raw snapshot 저장
→ content hash 비교
→ LLM normalized 후보 생성
→ 변경 분류와 로컬 후보 저장
```

첫 대상인 키움 공식 FAQ는 일반 HTTP만으로 본문을 얻을 수 있었다. 같은
본문으로 다시 실행하면 기존 pending candidate와 raw snapshot을 재사용해
중복 후보를 만들지 않았다.

처음 생성된 음식물 후보에는 주소, 전화번호, 주류와 재입장 정보가 한
문서에 섞였다. 원인은 FAQ 답변 뒤의 이웃 FAQ와 footer까지 parser가
가져온 것이었다. 이를 계기로 범용 parser에 의존하지 않고, 고척 FAQ의
음식물·캔 답변 블록과 KBO SAFE 페이지의 정책·예외 블록만 추출하도록
범위를 좁혔다.

관련 커밋은 `1843eb5 feat: add stadium guide candidate pipeline`이다.

## 11. Phase 3: 후보 검수와 로컬 적용

후보 관리는 다음 명령으로 분리했다.

```bash
python scripts/sync_stadium_guides.py candidates list --status pending
python scripts/sync_stadium_guides.py candidates show <candidate_id>
python scripts/sync_stadium_guides.py candidates approve <candidate_id>
python scripts/sync_stadium_guides.py candidates reject <candidate_id> --reason "<사유>"
python scripts/sync_stadium_guides.py apply-local <candidate_id>
```

`show`는 후보 생성 당시 source check와 raw snapshot을 기준으로 기존
내용, 후보 내용, 문장 단위 diff, 출처, 기준일과 limitation을 보여준다.
최신 수집 결과를 대신 사용하면 검수한 근거와 적용 근거가 달라질 수 있기
때문이다.

승인은 상태만 바꾸며 임베딩하지 않는다. `apply-local`은 embedding
직전과 DB transaction 안에서 활성 revision과 hash를 다시 확인한다.
후보가 생성된 뒤 다른 revision이 활성화됐다면 오래된 후보를 적용하지
않는다.

관련 커밋은 다음 두 개다.

```text
1c6d6a4 feat: add stadium guide review and local apply pipeline
a5a5c22 feat: complete stadium guide phase 3 rollout
```

## 12. 첫 적용 결과: 고척 안내와 KBO 공통 정책

초기 결과가 잘못 섞인 후보 4개는 반려하고 parser와 LLM 문서 경계를
보강한 뒤 다시 생성했다.

| 반려 후보 | 이유 |
|---|---|
| 고척 food 1차 | 주류·용기·재입장·주소·전화번호 혼재 |
| 고척 entry 1차 | 주류·용기·선예매·연간회원 혼재 |
| 고척 bag 1차 | 캔 총용량을 주류 총용량으로 축소 해석 |
| KBO 공통 bag 1차 | 가방 크기·개수 누락, 매점 판매 규칙 혼재 |

공식 근거와 limitation을 다시 검수해 다음 4개 후보를 승인했다.

| 문서 | candidate ID | revision ID |
|---|---|---|
| KBO 공통 반입 정책 | `SGC_20260911T005413_5cb4de4620` | `KBO_common_stadium_bag_policy_r0001` |
| 고척 음식물 안내 | `SGC_20260911T004205_c6db1d8010` | `GOCHEOK_stadium_food_guide_r0001` |
| 고척 반입 정책 | `SGC_20260911T004728_256571a4e6` | `GOCHEOK_stadium_bag_policy_r0001` |
| 고척 입장 안내 | `SGC_20260911T004343_0399aa1274` | `GOCHEOK_stadium_entry_guide_r0001` |

문서별 경계는 다음과 같이 잡았다.

```text
food: 구장 내 취식, 최초 입장 음식물, 재입장 시 외부 음식 제한
bag: 캔·병·PET·주류·피처·생수 제한
entry: 최초 입장과 재입장에 필요한 최소 교차 정보
common bag: 가방 크기·개수, 용기, 위험 물품, 구장별 예외
```

원문이 명확히 구분하지 않은 `총량 1L`의 적용 대상과 `올 시즌부터`
같은 상대적 시점은 임의로 해석하지 않고 limitation과 기준일로 남겼다.

## 13. 실제로 변경된 문서만 임베딩했는가

승인한 후보를 KBO 공통 bag, 고척 food, bag, entry 순으로 적용했다.

```text
적용 전 rag_documents: 5
적용 전 rag_chunks: 5
CREATE: 4
UPDATE: 0
DELETE_CANDIDATE 적용: 0
문서 embedding 요청: 4회
문서 embedding 입력: 4개
적용 후 rag_documents: 9
적용 후 rag_chunks: 9
```

평가는 성공 4회와 수정 후 재평가 2회를 수행했다. 평가기는 한 실행의
질문을 한 번에 embedding하므로 평가 query embedding은 6회 요청,
총 104개 질문 입력이었다. 문서 임베딩 4회를 포함하면 이번 로컬 적용에서
embedding endpoint 요청은 총 10회였다.

같은 네 candidate를 다시 `apply-local`했을 때 모두
`already_applied=true`를 반환했다.

```text
추가 revision: 0
추가 문서 embedding: 0
중복 chunk: 0
논리 문서별 활성 revision: 정확히 1개
```

## 14. 로컬 검색 평가는 기존 기준과 함께 본다

새 고척 문서가 자신의 질문에서 상위에 나오는지 확인하면서 기존 사직
15개 case도 함께 실행했다. 사직 baseline에 이미 존재하던 Top1 실패
`sajik_011`과 negative threshold 초과 `sajik_008`이 늘어나지 않는 것을
통과 기준으로 삼았다.

| 적용 문서 | 대상 평가 | 사직 회귀 | 결과 |
|---|---|---|---|
| KBO 공통 bag | Top1 3/3, Top3 3/3 | Top1 11/12, Top3 12/12 | 통과 |
| 고척 food | Top1 3/3, Top3 3/3 | Top1 11/12, Top3 12/12 | 통과 |
| 고척 bag | Top1 3/3, Top3 3/3 | Top1 11/12, Top3 12/12 | 통과 |
| 고척 entry | Top1 1/1, Top3 1/1 | Top1 11/12, Top3 12/12 | 통과 |

평가 결과에는 검색 순위뿐 아니라 target 문서의 `source_ids`,
`source_urls`, `as_of`가 비어 있지 않은지도 포함했다. 관련 결과는
`data/stadium_guide/evaluation/runs/candidate/`에 보존했다.

## 15. 평가 실패가 찾아낸 두 가지 문제

### 공통 문서가 구장별 문서보다 먼저 나온 문제

첫 KBO 공통 정책 평가에서는 고척 target은 통과했지만 사직 회귀가 크게
떨어졌다. SQL은 다음처럼 구장 일치 여부를 내림차순 정렬하고 있었다.

```sql
order by (chunks.stadium_id = :stadium_id) desc, distance
```

공통 문서의 비교 결과는 `false`가 아니라 `NULL`이다. PostgreSQL의
`DESC` 정렬에서는 별도 지정이 없으면 NULL이 먼저 와서 공통 문서가
구장별 문서를 밀어냈다.

```sql
order by
  (chunks.stadium_id = :stadium_id) desc nulls last,
  distance
```

`NULLS LAST`를 추가한 뒤 같은 candidate를 재실행했다. 이미 생성한
revision과 embedding은 재사용했고 평가만 다시 실행해 통과했다.

### 입장 평가 질문에 음식물 의도가 섞인 문제

첫 entry 평가는 입장 문서가 2위, food 문서가 1위였다.

```text
고척돔 재입장할 때 외부 음식을 다시 가져갈 수 있어?
```

질문은 재입장과 음식물이라는 두 의도를 함께 갖고 있었다. entry 문서만
1위여야 한다는 기대와 질문 자체가 맞지 않았다. food 정책 검증은 별도
case에 이미 있으므로 entry case를 재입장 가능 여부와 절차에 집중하도록
바꿨다.

```text
고척돔에서 경기 중 나갔다가 다시 입장할 수 있어? 재입장 절차가 궁금해.
```

재평가에서는 entry 문서가 Top1에 나왔고 사직 회귀 결과도 유지됐다.

## 16. 로컬 완료 상태

Phase 3 종료 시 로컬 DB 상태는 다음과 같다.

```text
rag_documents=9
rag_chunks=9
ready_for_production=4
rejected=4
completed_local_deployments=4
중복 활성 revision=0
중복 document_id·chunk_index=0
```

로컬 적용 transaction을 rollback하는 통합 검증에서도 승인, revision과
chunk 생성, 평가 상태 전이와 재실행 멱등성을 확인했다.

```text
phase3_transaction=passed
idempotent_reapply=passed
verify_candidates=0
verify_documents=0
```

변경 범위 lint와 type check가 통과했고 백엔드 API 테스트는 69개가
통과했다.

## 17. 운영 반영에서 발견한 schema 불일치

로컬 작업 후 백엔드가 운영 DB를 바라보는 상태에서 키움 예매 안내를
검색했더니 Tool 실패와 전체 채팅 스트림 실패가 이어졌다. 운영 DB에는
고척 예매 문서가 있었지만 새 retriever가 요구하는
`is_active`, `logical_document_id`, `legacy_unreviewed` 컬럼이 없었다.

```text
새 backend 코드
→ revision 컬럼을 사용하는 검색 SQL 실행
→ 아직 migration되지 않은 운영 DB에서 실패
→ 실패한 DB transaction이 남음
→ assistant 메시지 저장도 실패
→ 화면에 Tool 오류와 stream 오류가 연속 표시
```

이 문제는 새 데이터의 품질 문제가 아니라 코드와 DB 배포 순서 문제였다.
다음 순서로 복구하고 운영 반영을 진행했다.

1. 운영 DB 백업과 migration 상태 확인
2. revision migration 적용
3. legacy 문서 backfill과 검색 호환성 확인
4. 평가를 통과한 4개 revision 승격
5. 예매·음식물·반입·입장 질문 검색 검증
6. 같은 승격 명령을 다시 실행해 멱등성 확인

도구의 DB 조회가 실패하면 즉시 transaction을 rollback한 뒤 fallback
답변을 저장하도록 보강했다. Supabase transaction pooler에서 prepared
statement 이름이 충돌하지 않도록 asyncpg의 prepared statement cache를
끄고 매 statement에 고유 이름을 사용하도록 연결 설정도 수정했다.

운영 migration 전후 문서와 chunk 수는 68/72로 유지됐다. 이후 로컬에서
평가를 통과한 4개 revision을 승격한 결과는 다음과 같다.

```text
운영 rag_documents: 68 → 72
운영 rag_chunks: 72 → 76
운영 completed promotion: 4
로컬·운영 content hash 일치: 4/4
로컬·운영 embedding 일치: 4/4
중복 활성 revision: 0
로컬 candidate 상태: promoted 4
```

고척에는 기존 legacy bag 문서가 있어 candidate의 revision 번호 1과
충돌했다. 기존 문서를 삭제하는 대신 legacy 전용 번호로 옮겨 비활성
보존하고, 검증한 `GOCHEOK_stadium_bag_policy_r0001`을 활성화했다.

## 18. 설계에서 실제 구현으로 바뀐 부분

| 항목 | 초기 생각 | 최종 구현 | 이유 |
|---|---|---|---|
| 후보 diff | 본문 전체 또는 줄 단위 | 문장 단위 diff | 정책 문장의 추가·삭제를 검수하기 쉬움 |
| 후보 근거 | 최신 source check 조회 | 후보 생성 당시 run snapshot 고정 | 검수 근거와 적용 근거의 불일치 방지 |
| stale 검사 | transaction 안에서 한 번 | embedding 전과 transaction 안에서 두 번 | 불필요한 API 호출과 경합 방지 |
| parser | 범용 본문 추출 중심 | 출처별 FAQ·정책 블록 지정 | 메뉴, footer와 이웃 FAQ 혼입 방지 |
| 공통 정책 정렬 | boolean DESC | DESC NULLS LAST | `stadium_id=null` 문서의 우선순위 보장 |
| 평가 오류 | 실행 예외로 종료 | `evaluation_failed` 상태와 결과 보존 | 실패 후보의 운영 승격 차단 |
| 운영 실행 | 로컬 완료 직후 반영 | 문서 정비와 별도 승인 후 반영 | migration과 데이터 승격을 분리해 검증 |

## 19. 이번 작업에서 확인한 것

가장 효과가 컸던 결정은 LLM 후보 생성과 서비스 반영 사이에 검수 가능한
candidate를 둔 것이다. parser나 prompt가 완벽하지 않아도 잘못된 문서를
반려하고 기존 검색 데이터를 유지할 수 있었다.

또한 평가 데이터도 항상 옳다고 가정할 수 없었다. 실제 사용자 질문에는
여러 의도가 섞일 수 있고, 특정 document type만 Top1이어야 한다는 기대가
질문과 충돌할 수 있다. 평가 실패를 모델이나 데이터 탓으로만 보지 않고
검색 SQL, 메타데이터와 평가 질문을 함께 살펴봐야 했다.

이번 구현에서 확인한 원칙은 다음과 같다.

```text
upsert는 저장 방식이고 변경 분류는 운영 정책이다.
승인과 적용을 분리해야 검수한 대상을 정확히 배포할 수 있다.
기존 revision을 남겨야 실패 중에도 서비스와 롤백 경로를 유지할 수 있다.
파일, embedding 입력, 활성 vector index를 각각 확인해야 한다.
신규 데이터 평가는 기존 검색 품질의 회귀와 함께 봐야 한다.
DB migration과 애플리케이션 배포 순서도 RAG 품질의 일부다.
```

## 20. 운영 검증 결과와 다음 작업

운영 반영 후 같은 네 candidate를 다시 승격했을 때 모두
`already_promoted=true`를 반환했고 문서와 chunk 수는 늘지 않았다.

```text
키움 예매 질문: 기존 GOCHEOK ticketing 문서 검색 성공, distance 0.4888
고척 음식물 질문: 신규 food revision 검색 성공, distance 0.5973
승격 재실행: 4/4 멱등
```

고척 bag을 이전 legacy revision으로 되돌리는 롤백도 운영 transaction
안에서 실행했다. transaction 안에서는 legacy 문서가 활성화됐고,
검증 transaction을 rollback한 뒤 신규 revision이 다시 활성 상태로
유지됐으며 테스트용 deployment row도 남지 않았다.

이제 남은 작업은 고척 외 구장으로 같은 흐름을 확대하는 것이다.

1. 구장별 문서 유형 coverage 점검
2. 공식 출처 parser 확대
3. legacy 문서를 승인 revision으로 점진적으로 교체
4. 필요할 때 실제 롤백 명령과 deployment 이력 점검
5. 문서가 길어질 때 multi-chunk 전략 재검토

## 21. 문서 점검

- [x] 실제 CREATE·반려·승인 결과를 기록했다.
- [x] 문서 embedding과 평가 embedding 사용량을 구분해 기록했다.
- [x] 로컬 평가 결과와 실패·수정 과정을 기록했다.
- [x] 멱등성과 rollback transaction 검증 결과를 기록했다.
- [x] 구현 과정에서 달라진 설계를 반영했다.
- [x] 운영 migration, 승격과 Tool 검증 결과를 기록했다.
- [x] 운영 승격 재실행과 rollback rehearsal 결과를 기록했다.
- [x] 미완성 placeholder와 HTML 주석을 제거했다.
- [x] 비밀값과 로컬 인증 정보를 포함하지 않았다.
