# Stadium Guide Incremental Sync Spec

> 라벨: `MVP2-RAG-DATA-REFRESH`
> 작성일: 2026-09-10
> 범위: 구장 안내 공식 출처 수집, 변경 분류, 검수, 증분 임베딩, 로컬 평가, 운영 승격과 롤백
> 상태: 구현 진행 중 — Phase 1 로컬 적용 완료

## 1. 목적

구장 안내 RAG 데이터를 전체 삭제·전체 재임베딩 방식이 아니라 신규, 변경, 삭제 후보, 변경 없음으로 분류해 증분 갱신한다.

1차 구현은 자동 스케줄러나 관리자 화면을 만들지 않는다. 운영자가 터미널에서 명령을 직접 실행하지만, 실행 이력, 멱등성, 승인, 평가 차단, 운영 승격과 롤백을 갖춘 운영 가능한 파이프라인을 목표로 한다.

첫 적용 대상은 실사용 QA에서 근거 부족이 확인된 고척스카이돔 음식물 반입 정보다. 이 사례로 수집부터 운영 검증까지 전체 흐름을 완성한 뒤 다른 구장으로 확장한다.

## 2. 현재 구현 상태

- [확인됨] 구장 기본 정보는 `kbo_stadiums`에서 직접 조회하고, 구장 안내 문서는 `rag_documents`, `rag_chunks`에서 검색한다.
  - `backend/app/domains/baseball/tool/get_stadium_info/`
  - `backend/app/domains/baseball/tool/search_stadium_guide/`
- [확인됨] normalized 구장 안내 문서는 9개 구장, 5개 유형, 총 45개다.
  - `data/stadium_guide/normalized/`
- [확인됨] 45개 문서의 기준일은 모두 `2026-07-29`이고 `review_status`는 모두 `needs_review`다.
- [확인됨] embedded input은 45개 chunk이며 현재 전략은 문서 1개당 chunk 1개다.
  - `data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl`
  - `backend/scripts/generate_stadium_guide_chunks.py`
- [실행 확인] 2026-09-10 로컬 DB에는 사직구장 문서와 chunk만 각각 5개 존재한다. 저장소의 45개 embedded input과 실제 로컬 vector index 상태가 일치하지 않는다.
- [확인됨] 임베딩 스크립트는 입력된 모든 chunk를 OpenAI Embedding API에 전달한 뒤 `document_id`, `chunk_id` 기준으로 upsert한다.
  - `backend/scripts/embed_stadium_guide_chunks.py`
- [확인됨] 현재 임베딩 설정은 `text-embedding-3-small`, 1536차원이다.
- [확인됨] 현재 `document_id`와 `chunk_id`에는 수집 날짜가 포함되어 있다.
- [확인됨] 공식 출처 registry에는 55개 항목과 `monthly`, `before_season`, `before_game_series`, `manual` 갱신 정책이 기록되어 있다.
  - `data/stadium_guide/sources.json`
- [확인됨] 공식 페이지를 다시 수집하고 이전 원문과 비교하는 구장 안내 수집기는 없다.
- [확인됨] 검색기는 `rejected`가 아닌 chunk를 사용하므로 현재 `needs_review` 문서도 검색 대상이다.
  - `backend/app/domains/baseball/tool/search_stadium_guide/retriever.py`
- [확인됨] 고척 반입 정책 문서는 캔, 병, 주류, PET 음료 제한을 담고 있지만 음식물 반입 가능 여부를 직접 뒷받침하지 않는다.
  - `data/stadium_guide/normalized/GOCHEOK/stadium_bag_policy.json`
- [확인됨] raw, normalized, embedded input, evaluation 데이터 디렉터리가 이미 분리되어 있다.
  - `data/stadium_guide/README.md`

## 3. 현재 방식의 문제

- [확인됨] 내용이 바뀌지 않은 chunk도 실행할 때마다 다시 임베딩된다.
- [확인됨] 날짜가 포함된 문서 ID로 새 문서를 만들면 이전 문서가 검색 DB에 함께 남을 수 있다.
- [확인됨] 이전 chunk를 비활성화하거나 현재 활성 버전만 검색하는 계약이 없다.
- [확인됨] 신규, 변경, 삭제 예정, 변경 없음을 실행 전에 보여주는 diff가 없다.
- [확인됨] 수집 실패와 실제 정보 삭제를 구분하는 단계가 없다.
- [확인됨] 검수 후보와 현재 서비스 중인 승인 데이터를 분리하지 않는다.
- [추론] 전체 삭제 후 재삽입은 실행 도중 실패할 경우 검색 데이터가 비거나 일부만 반영될 위험이 있다.
- [추론] 공통 KBO 정책을 구장별 문서에 복제하면 정책 변경 시 중복 수정과 부분 갱신이 발생할 수 있다.

## 4. 확정된 운영 원칙

### 4.1 반자동 파이프라인

- 공식 출처 수집, 변경 감지, 작업 분류, LLM 초안 생성은 자동화한다.
- 검수와 승인은 문서 단위로 사람이 수행한다.
- 승인, 로컬 반영·평가, 운영 반영은 서로 다른 명령으로 실행한다.
- 관리자 웹 화면은 만들지 않는다.
- cron과 스케줄러는 구현하지 않는다.
- 모든 수집과 반영은 운영자가 터미널에서 직접 실행한다.
- `refresh_policy`는 자동 실행 설정이 아니라 권장 확인 주기로 사용한다.

### 4.2 안전한 데이터 교체

- 새 후보를 검수하는 동안 기존 활성 버전을 계속 제공한다.
- 승인된 새 revision을 반영할 때 이전 버전을 비활성화하고 새 버전을 활성화한다.
- 활성 버전 교체는 하나의 DB 트랜잭션으로 수행한다.
- 수집 실패, 빈 페이지, 로그인 화면, 접근 차단은 삭제로 판단하지 않는다.
- 기존 정보의 소실은 정상 수집 결과에서 두 번 연속 확인된 경우에만 `DELETE_CANDIDATE`로 만든다.
- 삭제 후보도 사람의 승인이 있어야 비활성화한다.
- 문서와 raw 이력은 물리 삭제하지 않는다.

### 4.3 로컬과 운영 분리

- 변경 후보, 검수 상태와 로컬 평가 이력은 로컬 DB에서 관리한다.
- 미검수 원문과 LLM 초안은 운영 DB에 저장하지 않는다.
- 운영 DB에는 승인된 revision, 활성 chunk와 배포·롤백 기록만 반영한다.
- 로컬 평가를 모두 통과한 동일 revision만 운영으로 승격한다.
- 평가 실패를 무시하는 강제 승격 옵션은 제공하지 않는다.

## 5. 범위

### 5.1 1차 구현 범위

1. source registry 검증과 DB 동기화
2. 일반 HTTP 수집기
3. 출처별 parser와 범용 fallback parser
4. 필요한 출처에 한정한 브라우저 수집 adapter
5. raw snapshot 저장과 source hash 비교
6. 문서별 `CREATE`, `UPDATE`, `DELETE_CANDIDATE`, `UNCHANGED`, `MANUAL_REQUIRED` 분류
7. LLM 기반 normalized 후보 생성
8. 후보 목록, 상세 diff, 승인, 반려 관리 명령
9. revision과 활성 버전 관리
10. 변경된 문서만 임베딩
11. 로컬 반영과 검색 평가
12. 평가를 통과한 revision의 운영 승격
13. 이전 revision 재활성화 방식의 롤백
14. 고척 음식물 반입 정보를 이용한 전체 흐름 검증

### 5.2 비목표

- [확정] cron, 배치 스케줄러, 외부 자동화 서비스 연결
- [확정] 관리자 웹 화면
- [확정] 웹 검색을 통한 신규 공식 출처 자동 발견
- [확정] 사용자 대화 전문의 수집 또는 학습
- [확정] 임베딩 모델 변경
- [확정] multi-chunk 전략 도입
- [확정] 공식 근거가 없는 문서 유형을 빈 내용으로 생성하는 작업
- [확정] 수집 결과를 사람 검수 없이 운영에 자동 반영하는 작업

## 6. 문서 유형

기존 5개 유형과 신규 3개 유형을 지원한다.

| document_type | 범위 |
|---|---|
| `stadium_bag_policy` | 캔, 병, 주류, PET 용량, 반입 금지 물품 |
| `stadium_facility_guide` | 화장실, 매장, 수유실, 편의시설 |
| `stadium_seat_guide` | 좌석 구역, 시야, 좌석 이용 안내 |
| `stadium_ticketing_guide` | 예매처, 발권, 취소, 환불 |
| `stadium_transport_guide` | 지하철, 버스, 주차, 셔틀 |
| `stadium_food_guide` | 외부 음식 반입, 취식, 구장 내 식음 매장 |
| `stadium_entry_guide` | 게이트, 입장 시간, 티켓 확인, 재입장, 입장 동선 |
| `stadium_accessibility_guide` | 휠체어석, 장애인 주차, 엘리베이터, 접근 가능한 출입구 |

공식 근거가 있는 유형만 문서를 생성한다. 구장마다 8개 문서를 강제로 만들지 않는다.

구장·문서 유형별 커버리지 상태는 다음 값을 사용한다.

```text
available
partial
missing_source
manual_required
collection_failed
```

## 7. 공통 정책 문서

KBO가 전체 구장에 적용한다고 명시한 정책은 `stadium_id=null`인 공통 문서로 관리한다.

첫 공통 문서는 다음과 같다.

```text
logical_document_id: KBO_common_stadium_bag_policy
stadium_id: null
document_type: stadium_bag_policy
source_id: kbo_safe_campaign
```

검색은 해당 구장 문서와 공통 문서를 함께 조회한다.

```text
1순위: 해당 구장 문서
2순위: KBO 공통 문서
```

구장별 정책과 공통 정책이 충돌하면 구장별 정책을 우선한다. 기준일과 적용 범위만으로 안전하게 해결할 수 없는 충돌은 자동 병합하지 않고 검수 대상으로 분류한다.

현재 구장별로 중복 등록된 KBO SAFE 출처는 공통 source ID 하나로 통합한다. 기존 source ID는 마이그레이션 매핑을 남겨 출처 이력을 유지한다.

## 8. Source Registry 계약

`data/stadium_guide/sources.json`을 출처 정의의 기준으로 사용하고 실행 상태는 DB에 저장한다.

registry가 관리할 필드는 다음과 같다.

```text
source_id
title
url
source_type
stadium_ids
team_ids
document_types
collector_type
parser_name
refresh_policy
trust_level
enabled
notes
```

규칙:

- 새 공식 출처는 사용자가 registry에 직접 추가한다.
- 파이프라인은 registry에 등록된 출처만 수집한다.
- 신규 URL을 검색엔진이나 LLM으로 자동 발견하지 않는다.
- `refresh_policy`는 `monthly`, `before_season`, `before_game_series`, `manual`을 유지한다.
- registry에서 제거된 출처는 즉시 삭제하지 않고 비활성화 후보로 분류한다.
- 실행 시작 전에 registry와 DB 상태 차이를 출력한다.
- 비밀값, 쿠키, Authorization header는 registry와 raw에 저장하지 않는다.

## 9. 수집과 raw 저장

### 9.1 수집 방식

공통 수집기가 HTTP 요청, 응답 검증, hash 계산과 raw 저장을 담당한다. 출처별 parser가 실제 본문 영역을 추출한다.

```text
일반 HTTP 수집
→ 출처별 parser
→ 범용 parser fallback
→ 본문 부족 또는 JavaScript 렌더링 감지
→ 출처별 브라우저 adapter
→ 실패 시 manual_required
```

브라우저 adapter는 필요한 출처에만 명시적으로 연결한다. 모든 출처를 브라우저로 수집하지 않는다.

### 9.2 raw 저장 위치

```text
data/stadium_guide/raw/<YYYY-MM-DD>/<STADIUM_OR_COMMON>/
```

raw 파일은 수정하지 않고 새 snapshot으로 추가한다. 같은 본문 hash의 snapshot은 중복 저장하지 않는다.

DB에는 다음 정보만 저장한다.

```text
source_id
source_url
collected_at
http_status
collector_type
parser_name
raw_content_hash
normalized_text_hash
raw_file_path
result_status
error_code
```

HTTP 200만으로 성공을 판단하지 않는다. 빈 본문, 로그인 화면, 차단 페이지, 예상 selector 부재를 별도 실패 상태로 기록한다.

## 10. 변경 분류 계약

분류 기준은 안정적인 `logical_document_id`, 내용 `content_hash`, 임베딩 모델과 활성 revision이다.

| 분류 | 조건 | 처리 |
|---|---|---|
| `CREATE` | 활성 논리 문서가 없음 | 새 후보 revision 생성 |
| `UPDATE` | 활성 문서가 있고 normalized `content_hash`가 다름 | 변경 후보 revision 생성 |
| `UNCHANGED` | 내용 hash와 임베딩 설정이 동일 | 임베딩과 DB 쓰기 생략 |
| `DELETE_CANDIDATE` | 정상 수집에서 내용 소실이 두 번 연속 확인됨 | 승인 전까지 기존 버전 유지 |
| `RE_EMBED` | 내용은 같지만 모델 또는 embedding 입력 계약이 변경됨 | 전체 또는 해당 chunk 재임베딩 |
| `MANUAL_REQUIRED` | 안정적으로 수집·추출·정규화할 수 없음 | 사람 확인 전 반영 금지 |

`RE_EMBED`는 이번 작업에서 실행 경로만 분류할 수 있게 설계하고, 실제 모델 변경은 수행하지 않는다.

여러 출처가 하나의 normalized 문서에 사용되면 출처별 후보를 만들지 않는다. 변경된 출처를 모두 반영한 최종 문서 revision 후보 하나를 생성하고, 보고서에 출처별 변경 내용을 함께 표시한다.

## 11. LLM normalized 후보 생성

LLM은 웹을 검색하거나 원천 데이터를 직접 수집하지 않는다. 규칙 기반 수집과 parser가 정리한 본문을 입력으로 사용한다.

입력:

```text
현재 활성 normalized 문서
변경된 공식 출처의 추출 본문
출처별 URL과 기준 시점
document_type별 허용 범위
```

출력:

```text
normalized 문서 후보
변경 요약
출처별 근거 매핑
삭제된 주장 목록
추가된 주장 목록
불확실하거나 충돌하는 항목
```

규칙:

- 출처에 없는 사실을 추가하지 않는다.
- 불확실한 내용은 단정하지 않고 limitation으로 남긴다.
- 전체 raw HTML이 아니라 parser가 정리한 본문만 전달한다.
- 구조화된 schema로 출력을 검증한다.
- 생성 또는 schema 검증 실패 시 `manual_required`로 전환한다.
- LLM 출력은 승인 전까지 서비스 검색에 사용하지 않는다.

## 12. Revision과 검색 모델

### 12.1 식별자

논리 문서 ID는 날짜와 무관하게 고정한다.

```text
logical_document_id: GOCHEOK_stadium_food_guide
revision_id: GOCHEOK_stadium_food_guide_r0001
chunk_id: GOCHEOK_stadium_food_guide_r0001_chunk_000
```

normalized schema는 다음 값을 포함한다.

```text
schema_version
logical_document_id
revision_id
revision_number
document_type
stadium_id
team_id
title
as_of
trust_level
review_status
sources
content
content_hash
metadata
```

### 12.2 저장과 활성화

- 승인된 normalized JSON은 저장소와 DB에 함께 유지한다.
- 저장소 파일과 DB revision의 `revision_id`, `content_hash` 일치 여부를 검사한다.
- 이전 revision과 embedding은 롤백을 위해 보존한다.
- 논리 문서별 활성 revision은 하나만 허용한다.
- 검색기는 활성 revision의 chunk만 조회한다.
- 신규 후보는 `rag_documents`, `rag_chunks` 검색 경로에 들어가지 않는다.

### 12.3 기존 문서 전환

- DB에 이미 존재하는 구장 안내 문서는 `legacy` 활성 데이터로 유지한다.
- 신규 파이프라인 도입 시 서비스를 중단하지 않는다.
- 기존 문서를 일괄 승인하지 않는다.
- 고척부터 검수된 revision으로 점진적으로 교체한다.
- 모든 대상이 교체된 뒤 legacy 검색 허용 경로를 제거한다.

로컬 적용 시점에는 사직구장 문서 5개가 legacy 활성 revision으로 전환됐다. 저장소에만 있고 로컬 DB에 없는 나머지 40개 입력은 legacy 전환 대상으로 간주하지 않으며, 이후 파이프라인에서 공식 출처 검수와 승인 절차를 거쳐 신규 revision으로 반영한다.

## 13. 제안 DB 모델

정확한 컬럼명은 migration 구현 중 현재 naming convention에 맞춰 조정할 수 있지만 역할은 다음과 같이 분리한다.

### 13.1 `stadium_guide_sync_runs`

수동 파이프라인 실행 한 건을 기록한다.

```text
run_id
scope
status
started_at
finished_at
source_count
create_count
update_count
unchanged_count
delete_candidate_count
manual_required_count
failure_count
```

### 13.2 `stadium_guide_source_checks`

출처별 수집 결과와 연속 소실 횟수를 기록한다.

```text
check_id
run_id
source_id
result_status
raw_content_hash
normalized_text_hash
raw_file_path
http_status
consecutive_missing_count
collected_at
error_code
```

### 13.3 `stadium_guide_change_candidates`

문서 단위 변경 후보와 검수 상태를 기록한다.

```text
candidate_id
run_id
logical_document_id
operation
previous_revision_id
candidate_revision_id
previous_content_hash
candidate_content_hash
candidate_payload
diff_summary
source_ids
status
reviewed_at
review_note
created_at
```

후보 상태:

```text
pending
approved
rejected
applied_local
evaluation_failed
ready_for_production
promoted
```

### 13.4 `rag_documents`와 `rag_chunks`

기존 테이블을 revision 지원 구조로 확장한다.

필요한 핵심 값:

```text
logical_document_id
revision_number
is_active
activated_at
deactivated_at
legacy_unreviewed
```

논리 문서별 활성 revision 하나를 보장하는 unique partial index를 둔다. 검색 query는 `is_active=true`를 필수 조건으로 사용한다.

### 13.5 `stadium_guide_deployments`

로컬 적용, 운영 승격과 롤백을 기록한다.

```text
deployment_id
candidate_id
revision_id
target
action
evaluation_run_id
previous_active_revision_id
status
deployed_at
error_code
```

운영 DB에는 승인된 revision과 운영 대상 deployment 기록만 저장한다.

## 14. CLI 계약

명령은 하나의 진입점 아래 하위 명령으로 구성한다. 최종 파일명은 구현 시 기존 script naming과 맞춘다.

```text
backend/scripts/sync_stadium_guides.py
```

### 14.1 수집과 후보 생성

```bash
uv run python scripts/sync_stadium_guides.py collect --stadium-id GOCHEOK
uv run python scripts/sync_stadium_guides.py collect --source-id heroes_gocheok_ticket_normal
uv run python scripts/sync_stadium_guides.py collect --all
```

출력:

```text
run_id
수집 성공·실패 수
CREATE 수
UPDATE 수
UNCHANGED 수
DELETE_CANDIDATE 수
MANUAL_REQUIRED 수
pending candidate ID 목록
```

### 14.2 후보 확인

```bash
uv run python scripts/sync_stadium_guides.py candidates list --status pending
uv run python scripts/sync_stadium_guides.py candidates show <candidate_id>
```

상세 출력에는 기존 내용, 후보 내용, 문장 단위 diff, 출처별 변경, 출처 URL, 기준일과 limitation을 포함한다.

### 14.3 승인과 반려

```bash
uv run python scripts/sync_stadium_guides.py candidates approve <candidate_id>
uv run python scripts/sync_stadium_guides.py candidates reject <candidate_id> --reason "<reason>"
```

승인은 후보 상태만 변경한다. 승인 명령에서 임베딩이나 DB 활성화를 수행하지 않는다.

### 14.4 로컬 반영과 평가

```bash
uv run python scripts/sync_stadium_guides.py apply-local <candidate_id>
```

처리:

```text
승인 상태 재검증
→ 현재 활성 revision과 hash 재검증
→ 변경된 문서만 임베딩
→ 새 revision과 chunk 저장
→ 로컬 활성 revision 교체
→ 대상 평가 실행
→ 공통 회귀 평가 실행
→ 성공 시 ready_for_production
→ 실패 시 evaluation_failed
```

### 14.5 운영 승격

```bash
uv run python scripts/sync_stadium_guides.py promote-production <candidate_id>
```

조건:

- 후보가 `ready_for_production` 상태여야 한다.
- 로컬에서 평가된 `revision_id`, `content_hash`, embedding 설정이 일치해야 한다.
- 필수 평가가 모두 통과해야 한다.
- 강제 승격 옵션은 제공하지 않는다.
- 운영 연결은 `PROD_DATABASE_URL`을 사용하고 비밀값을 출력하지 않는다.

### 14.6 롤백

```bash
uv run python scripts/sync_stadium_guides.py rollback-production \
  --logical-document-id GOCHEOK_stadium_food_guide \
  --revision-id GOCHEOK_stadium_food_guide_r0001
```

롤백은 삭제나 백업 복원이 아니라 이전 승인 revision의 재활성화다. 현재 활성 revision, 복구 revision과 실행 결과를 deployment 이력에 기록한다.

## 15. 멱등성과 트랜잭션

- 같은 source snapshot을 다시 수집해도 중복 raw와 후보를 만들지 않는다.
- 같은 `candidate_content_hash`의 pending 또는 approved 후보가 있으면 새 후보를 만들지 않는다.
- 이미 적용된 candidate의 `apply-local` 재실행은 성공 상태를 반환하고 중복 revision을 만들지 않는다.
- 이미 승격된 revision의 운영 승격 재실행은 중복 row를 만들지 않는다.
- 문서, chunk와 활성 revision 교체는 하나의 트랜잭션으로 처리한다.
- 임베딩 API 실패 시 DB 활성 버전을 변경하지 않는다.
- DB 실패 시 후보 상태를 성공으로 기록하지 않는다.
- 부분적으로 생성된 embedding은 활성화하지 않는다.

## 16. 검색 변경

`search_stadium_guide`와 `search_ticketing_guide`는 활성 revision만 조회해야 한다.

구장 안내 검색 대상에는 신규 유형을 추가한다.

```text
stadium_bag_policy
stadium_facility_guide
stadium_seat_guide
stadium_transport_guide
stadium_food_guide
stadium_entry_guide
stadium_accessibility_guide
```

예매 검색은 기존처럼 `stadium_ticketing_guide`를 별도로 사용한다.

구장 안내 검색은 다음 조건을 적용한다.

```text
해당 stadium_id의 활성 chunk
OR stadium_id가 null인 활성 공통 chunk
```

동일 주제에서는 구장별 문서를 공통 문서보다 우선한다. legacy 전환 기간에는 명시적으로 표시된 기존 활성 문서만 예외적으로 허용한다.

## 17. 로컬 평가와 운영 차단 조건

로컬 반영 후 두 종류의 평가를 모두 실행한다.

### 17.1 변경 영역 평가

첫 적용에서는 다음 질문을 포함한다.

```text
고척돔 음식물 반입 가능해?
고척돔에 외부 음식 가져가도 돼?
고척돔에 캔이나 병을 가져갈 수 있어?
고척돔에서 술을 반입할 수 있어?
고척돔 PET 음료 제한이 어떻게 돼?
```

확인 항목:

- 기대 document type이 검색되는가
- 구장별 문서와 KBO 공통 정책이 올바른 순서로 검색되는가
- 음식물과 음료 용기 정책을 혼동하지 않는가
- 출처가 직접 뒷받침하지 않는 내용을 단정하지 않는가
- 활성 revision만 검색되는가

### 17.2 공통 회귀 평가

- 기존 구장 안내 평가 케이스를 실행한다.
- 기존 기준선에 없던 신규 실패가 없어야 한다.
- source URL, `as_of`, `review_status`가 유지되는지 확인한다.
- 이전 revision이 일반 검색 결과에 나타나지 않는지 확인한다.
- 공통 문서가 관련 없는 구장 안내 질문을 오염시키지 않는지 확인한다.

필수 평가가 하나라도 실패하면 `promote-production`을 차단한다. 예외 또는 force 옵션은 없다.

## 18. 첫 적용: 고척 음식물 반입

고척 사례의 목표는 결론을 미리 정해 넣는 것이 아니라 공식 출처에서 직접 확인 가능한 범위를 분리하는 것이다.

예상 문서 구성:

```text
GOCHEOK_stadium_food_guide
→ 외부 음식 반입, 취식, 구장 내 식음 관련 근거

GOCHEOK_stadium_bag_policy
→ 캔, 병, 주류, PET 용량과 반입 제한

KBO_common_stadium_bag_policy
→ KBO 전체 구장 공통 안전·반입 기준
```

완료 조건:

1. 관련 공식 출처가 registry에 등록되어 있다.
2. 수집 raw와 source check가 생성된다.
3. 기존 문서와 신규 정보가 `CREATE` 또는 `UPDATE`로 올바르게 분류된다.
4. LLM 후보가 출처 근거를 벗어나지 않는다.
5. 문서별 승인과 로컬 반영이 분리되어 동작한다.
6. 변경된 문서만 임베딩된다.
7. 고척 전용 평가와 공통 회귀 평가를 모두 통과한다.
8. 동일 revision이 운영 DB에 승격된다.
9. 운영 검색에서 새 활성 revision과 출처를 확인한다.
10. 재실행 시 중복 revision이나 chunk가 생성되지 않는다.

## 19. 테스트와 검증

### 19.1 단위 테스트

- source registry schema 검증
- hash 정규화와 동일 본문 판정
- CREATE, UPDATE, UNCHANGED 분류
- 수집 실패와 DELETE_CANDIDATE 구분
- 두 번 연속 소실 조건
- candidate 상태 전이
- 안정적인 logical ID와 revision ID 생성
- LLM 구조화 출력 검증
- 공통 문서와 구장 문서 우선순위

### 19.2 통합 테스트

- 동일 수집을 두 번 실행했을 때 두 번째 실행이 UNCHANGED인지 확인
- 변경된 문서만 embedding API 입력이 되는지 확인
- 임베딩 실패 시 기존 활성 revision 유지
- 새 revision 활성화와 이전 revision 비활성화의 원자성 확인
- rejected 후보가 반영되지 않는지 확인
- 로컬 평가 실패 시 운영 승격 차단
- 운영 승격 재실행의 멱등성 확인
- 이전 revision 롤백 확인

### 19.3 실제 데이터 검증

- 고척 공식 출처 수집
- normalized JSON과 DB revision hash 비교
- 로컬 pgvector 검색 평가
- 운영 승격 후 read-only 조회
- 사용자 질문 형태의 Tool 실행 검증

DB 접속, migration, embedding, seed와 운영 반영은 저장소 규칙에 따라 실행 전에 사용자 승인을 받는다.

### 19.4 Phase 1 로컬 검증 결과

2026-09-10 사용자 승인 후 로컬 Supabase에 migration을 적용했다.

```text
migration version: 20260910090000
pipeline tables: 4
local stadium guide documents: 5
logical document ids: 5
active legacy revisions: 5
duplicate active revisions: 0
common document retrieval transaction: passed
candidate table write and rollback transaction: passed
application retriever legacy search: 4 guide chunks
Supabase schema lint: no errors
backend API tests: 59 passed
```

애플리케이션 retriever의 4개 결과는 사직구장의 반입, 시설, 좌석, 교통 문서다. 예매 문서 1개는 별도 `search_ticketing_guide` 검색 설정에 속하므로 구장 안내 검색 결과에서 제외되는 것이 정상이다.

검증용 공통 문서, sync run, source check와 candidate row는 같은 transaction에서 생성한 뒤 rollback했으며 로컬 DB에 남지 않았다.

## 20. 실패 처리

| 실패 | 처리 |
|---|---|
| HTTP timeout | source check 실패 기록, 기존 데이터 유지 |
| 접근 차단 | 브라우저 adapter 시도 후 `manual_required` |
| parser 실패 | raw 보존, 후보 미생성, `manual_required` |
| LLM 생성 실패 | 후보 미승인 상태 유지 또는 `manual_required` |
| schema 검증 실패 | 후보 반영 금지 |
| embedding API 실패 | 활성 revision 변경 없음 |
| 로컬 DB 실패 | transaction rollback |
| 평가 실패 | `evaluation_failed`, 운영 승격 차단 |
| 운영 DB 실패 | 기존 운영 revision 유지, 실패 deployment 기록 |
| rollback 실패 | 현재 활성 revision 유지, 실패 기록 |

## 21. 보안과 운영 기록

- `.env`, API key, DB 비밀번호, Authorization header, 쿠키를 raw, DB, 로그와 보고서에 기록하지 않는다.
- 로그에 출력하는 DB URL은 비밀번호를 마스킹한다.
- 후보에는 실제 사용자 대화를 저장하지 않는다.
- 평가 질문은 합성된 고정 case만 사용한다.
- raw snapshot에는 요청에 사용한 인증 정보를 포함하지 않는다.
- 브라우저 adapter는 공개 공식 페이지에만 사용한다.

## 22. 구현 순서

### Phase 1. 데이터 모델과 기존 데이터 전환

- [x] revision, candidate, sync run, source check, deployment migration 작성
- [x] 로컬 DB에 존재하는 기존 구장 안내 문서를 legacy 활성 revision으로 매핑
- [x] 검색 query에 활성 revision과 승인·legacy 조건 추가
- [x] 공통 문서 조회 지원
- [x] 로컬 migration 적용과 트랜잭션 기반 검증

### Phase 2. 수집과 후보 생성

1. source registry schema 확장과 공통 출처 통합
2. 공통 HTTP collector 작성
3. 고척 출처 parser 작성
4. 필요한 브라우저 adapter 작성
5. raw 저장과 source check 기록
6. 변경 분류와 문서별 후보 생성
7. LLM normalized 초안 생성

### Phase 3. 검수와 로컬 적용

1. 후보 목록·상세 diff 명령
2. 승인·반려 명령
3. 변경분 임베딩
4. 로컬 revision 활성화
5. 고척 전용 평가와 공통 회귀 평가

### Phase 4. Blog 6 작성과 구현 결과 반영

1. 이 spec을 기반으로 Blog 6 초안 생성
2. 구현 전 문제와 설계 결정을 먼저 기록
3. 실제 구현 결과, 실패와 평가 수치를 반영해 글 완성
4. Blog 5에는 다음 작업을 연결하는 짧은 문단만 추가

### Phase 5. 운영 승격

1. 사용자 승인 후 운영 migration 적용
2. 평가를 통과한 고척 revision 승격
3. 운영 DB의 활성 revision과 chunk 확인
4. 운영 Tool 검색 검증
5. 멱등 재실행 확인

## 23. 전체 완료 기준

다음 조건을 모두 충족해야 1차 파이프라인이 완료된 것으로 본다.

- 수동 명령으로 고척 출처를 수집할 수 있다.
- 신규, 변경, 변경 없음, 삭제 후보와 수동 검토 필요 상태를 구분한다.
- LLM 초안과 사람 승인이 분리되어 있다.
- 문서별 승인 후 로컬 반영을 별도로 실행할 수 있다.
- 변경된 문서만 임베딩한다.
- 활성 revision 하나만 검색된다.
- 기존 버전을 유지한 상태에서 새 버전을 검수하고 원자적으로 교체한다.
- 고척 전용 평가와 전체 회귀 평가가 통과한다.
- 평가 실패 시 운영 승격이 불가능하다.
- 승인·평가된 동일 revision이 운영에 반영된다.
- 운영 조회에서 새 근거와 출처가 확인된다.
- 재실행이 멱등하다.
- 이전 승인 revision으로 롤백할 수 있다.
- raw, normalized, candidate, revision과 deployment 이력을 추적할 수 있다.
- Blog 6에 최종 구현 과정과 검증 결과가 반영된다.

## 24. 열린 항목

- [확인 필요] 고척 음식물 반입을 직접 설명하는 최신 공식 출처와 문구
- [확인 필요] 고척 공식 페이지 중 브라우저 adapter가 필요한 URL
- [확인 필요] normalized 문서가 `manual_required`로 전환되는 최대 길이 기준
- [확인 필요] 기존 45개 legacy 문서의 구장별 검수 순서
- [확인 필요] 운영 migration과 첫 revision 승격의 실제 실행 시점

위 항목은 구현과 공식 출처 조사에서 확인한다. 파이프라인의 핵심 구조를 다시 결정해야 하는 열린 질문은 없다.
