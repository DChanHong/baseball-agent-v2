# 구장 안내 파이프라인 다음 작업과 검수 메모

작성일: 2026-09-10  
기준 커밋: `1843eb5 feat: add stadium guide candidate pipeline`

## 1. 현재 상태

Phase 2까지 완료했다.

- 등록된 공식 출처만 읽는 수집기를 구현했다.
- 고척 전용 parser와 선택적 브라우저 adapter를 구현했다.
- raw snapshot과 source check 이력을 로컬 DB에 저장한다.
- 변경을 `CREATE`, `UPDATE`, `UNCHANGED`, `DELETE_CANDIDATE`, `MANUAL_REQUIRED`로 분류한다.
- LLM이 normalized 후보를 만들지만 검색용 RAG 데이터에는 자동 반영하지 않는다.
- 같은 출처 내용으로 다시 실행하면 기존 pending 후보와 raw snapshot을 재사용한다.
- collect 명령은 localhost가 아닌 `DATABASE_URL`을 거부한다.

현재 로컬 DB 상태:

```text
RAG documents: 5
RAG chunks: 5
sync runs: 2
source checks: 2
pending candidates: 1
raw snapshots: 1
```

현재 후보:

```text
candidate_id: SGC_20260910T055139_cd999a2da2
logical_document_id: GOCHEOK_stadium_food_guide
operation: CREATE
status: pending
source_id: heroes_gocheok_faq
```

이 후보는 아직 승인, 임베딩, 활성화 또는 운영 반영되지 않았다.

## 2. 다음 구현 작업: Phase 3

### 2.1 후보 조회

다음 명령을 구현한다.

```bash
uv run python scripts/sync_stadium_guides.py candidates list --status pending
uv run python scripts/sync_stadium_guides.py candidates show <candidate_id>
```

상세 화면에는 다음 내용을 출력한다.

- 논리 문서 ID와 변경 분류
- 이전 revision과 후보 revision
- 이전·후보 content hash
- 기존 내용과 후보 내용
- 문장 단위 diff
- 사용한 source ID와 공식 URL
- 출처별 추출 근거
- 기준일과 limitations

### 2.2 승인과 반려

다음 명령을 구현한다.

```bash
uv run python scripts/sync_stadium_guides.py candidates approve <candidate_id>
uv run python scripts/sync_stadium_guides.py candidates reject <candidate_id> --reason "<사유>"
```

승인은 후보 상태만 변경한다. 승인 명령에서 임베딩하거나 활성 revision을 교체하지 않는다.

### 2.3 로컬 적용

다음 명령을 구현한다.

```bash
uv run python scripts/sync_stadium_guides.py apply-local <candidate_id>
```

처리 순서:

1. 후보가 approved 상태인지 확인한다.
2. 후보 생성 이후 활성 revision이 바뀌지 않았는지 확인한다.
3. 변경된 문서 한 건만 `text-embedding-3-small`로 임베딩한다.
4. 새 `rag_documents` revision과 chunk를 저장한다.
5. 같은 트랜잭션에서 기존 revision을 비활성화하고 새 revision을 활성화한다.
6. 고척 전용 평가와 전체 회귀 평가를 실행한다.
7. 통과하면 `ready_for_production`, 실패하면 `evaluation_failed`로 기록한다.

### 2.4 평가

고척 음식물 전용 평가 case를 추가한다.

- 구장 내 음식물 섭취 가능 여부
- 최초 입장 시 외부 음식 반입 조건
- 재입장 시 외부 음식 반입 제한
- 병, 캔, PET 용기 조건
- 주류 도수 및 총용량 조건
- 구장별 정책과 KBO 공통 정책의 우선순위
- 출처와 기준일 표시

기존 사직구장 검색 결과가 유지되는지도 함께 확인한다.

## 3. 사용자가 검수해야 할 내용

### 3.1 문장별 공식 근거

키움 히어로즈 공식 FAQ 원문과 아래 후보 주장을 대조한다.

- 구장 내 음식물 섭취가 가능하다는 내용
- 최초 입장 시 음식물을 반입할 수 있다는 내용
- 병에 담긴 음식물 또는 음료의 제한 조건
- 재입장 시 외부 음식 반입이 제한된다는 내용
- 8도 이하 주류만 허용된다는 내용
- 캔 반입 총용량이 1인당 1L라는 내용
- 특정 피처, 컵와인, 팩소주, 플라스틱 용기의 제한 내용

공식 출처:

- https://heroesbaseball.co.kr/mobile/fans/qna/list.do

### 3.2 문서 유형 분리

현재 후보에 음식물, 용기, 주류, 재입장 정보가 함께 들어 있다. 다음 기준으로 나눌지 결정해야 한다.

| 내용 | 권장 문서 유형 |
|---|---|
| 음식물 섭취와 외부 음식 | `stadium_food_guide` |
| 병·캔·PET·주류 제한 | `stadium_bag_policy` |
| 재입장 시 외부 음식 제한 | `stadium_entry_guide`와 `stadium_food_guide` 중복 검토 |

권장안은 각 문서가 자신의 질문에 독립적으로 답할 수 있는 최소한의 교차 정보만 유지하는 것이다. 같은 문장을 세 문서에 그대로 복제하지 않는다.

### 3.3 후보에서 제거하거나 수정할 내용

현재 후보에는 음식물 안내와 직접 관련 없는 구장 주소와 전화번호가 포함돼 있다. 승인 전에 제거한다.

`올 시즌`, `현재` 같은 표현은 시간이 지나면 의미가 달라지므로 다음 중 하나로 정리한다.

- 기준일을 문장에 명시한다.
- 지속 여부를 확인할 수 없으면 limitation으로 이동한다.
- 시즌이 확정되지 않은 표현은 삭제한다.

LLM 생성 prompt에는 이후 후보부터 주소·전화번호·메뉴 등 공통 영역을 제외하도록 보강해 두었다.

### 3.4 승인 직전 확인

- 후보 본문에 공식 출처에 없는 해석이 없는가?
- food, bag, entry 문서 유형의 경계가 적절한가?
- 기준일이 2026-09-10으로 기록됐는가?
- 출처 URL과 source ID가 맞는가?
- 불확실한 내용이 limitation에 들어갔는가?
- 삭제된 주장과 추가된 주장을 diff로 이해할 수 있는가?

위 항목을 모두 확인한 뒤에만 approve한다.

## 4. 로컬 실행 시 주의할 점

현재 `backend/.env`의 `DATABASE_URL`과 `PROD_DATABASE_URL`은 운영 주소를 가리킨다. Phase 3의 후보 조회·승인·로컬 적용은 로컬 Supabase를 대상으로 해야 한다.

예시:

```bash
cd backend
DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres' \
  uv run python scripts/sync_stadium_guides.py candidates list --status pending
```

collect 명령에는 운영 DB 오접속 방지 검사가 들어 있다. Phase 3에서 추가할 후보 조회, 승인, 반려와 `apply-local`에도 같은 검사를 적용한다.

## 5. Phase 3 이후

### Phase 4

- Blog 6의 실제 diff와 검수 결과를 채운다.
- 실제 임베딩 호출 수와 평가 결과를 기록한다.
- 구현 과정에서 발견한 실패와 수정 내용을 반영한다.

### Phase 5

- 사용자의 최종 승인 후 운영 migration 상태를 확인한다.
- 로컬에서 평가를 통과한 동일 revision만 운영에 승격한다.
- 운영 검색 결과와 출처를 확인한다.
- 같은 승격 명령의 재실행이 중복 데이터를 만들지 않는지 확인한다.
- 문제 발생 시 이전 승인 revision으로 롤백한다.

운영 반영은 Phase 3 평가와 사용자 검수가 끝나기 전에는 진행하지 않는다.
