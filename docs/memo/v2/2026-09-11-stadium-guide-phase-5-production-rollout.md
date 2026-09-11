# 구장 안내 파이프라인 Phase 5 운영 반영 결과

> 실행일: 2026-09-11
> 상태: 완료
> 범위: 운영 migration, revision 승격, 검색 검증, 멱등성과 롤백 경로 검증

## 적용 내용

운영 DB에 `20260910090000_add_stadium_guide_revision_pipeline` migration을
적용했다. 기존 68개 문서를 revision 구조로 backfill한 뒤, 로컬에서 승인과
평가를 마친 다음 4개 revision을 운영에 승격했다.

| 문서 | candidate ID | 운영 revision ID | 이전 활성 revision |
|---|---|---|---|
| KBO 공통 반입 정책 | `SGC_20260911T005413_5cb4de4620` | `KBO_common_stadium_bag_policy_r0001` | 없음 |
| 고척 음식물 | `SGC_20260911T004205_c6db1d8010` | `GOCHEOK_stadium_food_guide_r0001` | 없음 |
| 고척 반입 정책 | `SGC_20260911T004728_256571a4e6` | `GOCHEOK_stadium_bag_policy_r0001` | `GOCHEOK_stadium_bag_policy_20260729` |
| 고척 입장 | `SGC_20260911T004343_0399aa1274` | `GOCHEOK_stadium_entry_guide_r0001` | 없음 |

고척 반입 정책은 운영의 legacy 문서와 revision 번호가 충돌했다. legacy
문서를 삭제하지 않고 보존용 번호로 이동해 비활성화한 뒤, 검증된 r0001을
활성화했다.

## 검증 결과

```text
운영 rag_documents: 68 -> 72
운영 rag_chunks: 72 -> 76
completed production promotion: 4
로컬·운영 content hash 일치: 4/4
로컬·운영 embedding 일치: 4/4
중복 활성 revision: 0
로컬 candidate 상태 promoted: 4/4
```

동일한 네 candidate의 승격 명령을 다시 실행했을 때 모두
`already_promoted=true`였고 문서와 chunk 수는 늘지 않았다.

운영 Tool 검색에서는 다음 결과를 확인했다.

```text
질문: 키움 티켓예매 어디서하나?
결과: GOCHEOK_stadium_ticketing_guide_20260729
distance: 0.4888

질문: 고척돔에 외부 음식 가져가도 돼?
결과: GOCHEOK_stadium_food_guide_r0001
distance: 0.5973
```

고척 반입 정책을 이전 legacy revision으로 되돌리는 명령도 운영
transaction 안에서 실행했다. transaction 내부에서 이전 문서가 활성화되는
것을 확인한 뒤 검증 transaction 전체를 rollback했다. 따라서 테스트용
deployment 기록은 남지 않았고, 최종 운영 상태에는 신규 r0001이 활성화되어
있다.

## 함께 수정한 장애 경로

운영 migration 전에 새 검색 SQL이 없는 revision 컬럼을 조회하면서 Tool이
실패했고, 실패한 PostgreSQL transaction 때문에 fallback 답변 저장도 연이어
실패했다. Tool 실패 시 세션을 rollback한 뒤 fallback 답변을 저장하도록
수정했다.

Supabase transaction pooler에서 prepared statement 이름이 충돌하는 문제를
피하도록 statement cache를 끄고 연결마다 고유한 statement 이름을 사용하게
했다.

## 이후 운영 방식

운영 승격은 자동 cron 없이 사용자가 터미널에서 candidate ID별로 실행한다.
수집, 검수, 로컬 적용·평가, 운영 승격을 각각 분리하며, 운영에는 로컬에서
평가를 통과한 동일 hash와 embedding만 복사한다. 장애가 생기면
`rollback-production` 명령으로 남아 있는 이전 승인 revision을 다시
활성화한다.
