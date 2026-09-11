# 구장 안내 Phase 3 후보 검수표

작성일: 2026-09-11
대상: 고척 구장별 안내 3개와 KBO 공통 반입 정책 1개

## 검수 전 상태

```text
rag_documents=5
rag_chunks=5
pending=4
```

아래 후보는 아직 승인, 임베딩 또는 활성 revision 교체가 되지 않았다.

## 1. 고척 음식물 안내

```text
candidate_id: SGC_20260911T004205_c6db1d8010
logical_document_id: GOCHEOK_stadium_food_guide
operation: CREATE
content_hash: 1a34e133f258b9c59e823f51c4a28fe13f14e64837242da6a52c76020810832c
as_of: 2026-09-11
source_id: heroes_gocheok_faq
```

후보 본문:

> 구장 내 음식물 섭취는 모두 가능합니다. 최초 입장 시에는 음식물 반입
> 가능하며, 병에만 담겨있지 않으면 됩니다. 단, 재입장 시에는 외부 음식
> 반입은 제한됩니다.

검수 결과:

- 음식물 섭취, 최초 입장과 재입장 관련 세 문장이 공식 FAQ에 있다.
- 주류, 캔 용량, 주소와 전화번호는 본문에서 제거됐다.
- `병에만 담겨있지 않으면 됩니다`는 공식 문구이지만 뜻이 모호하므로
  허용 용기를 임의로 해석하지 않고 limitation에 남겼다.

권장 결정: **승인**

## 2. 고척 반입 정책

```text
candidate_id: SGC_20260911T004728_256571a4e6
logical_document_id: GOCHEOK_stadium_bag_policy
operation: CREATE
content_hash: 02b344be4b4b22bc2c12e52812e1aee9f2284a62078f00006e2ae76af26273b0
as_of: 2026-09-11
source_id: heroes_gocheok_faq
```

후보가 포함하는 내용:

- 캔은 원문의 `올 시즌부터` 허용 문구와 함께 1인당 총 1L까지로 안내한다.
- 주류는 8도 이하만 허용된다고 안내한다.
- 맥주 1.6L 피처, 컵와인, 팩소주와 플라스틱 용기 소주를 반입 불가
  예시로 둔다.
- 맥주 500ml 캔 2개, 맥주 1L 피처 1개와 생수 1.8L 불가를 원문의
  총용량 예시로 둔다.
- KBO SAFE 캠페인을 따른다는 공식 문구를 포함한다.

검수 결과:

- 원문이 총 1L의 적용 대상을 주류 또는 전체 음료로 명확히 구분하지 않는다.
  후보도 적용 대상을 임의로 확정하지 않고 limitation에 남겼다.
- `올 시즌부터`가 어느 시즌을 뜻하는지 불명확하고 향후 변경될 수 있음을
  limitation에 기록했다.
- 음식물 섭취와 재입장 절차는 제거됐다.

권장 결정: **승인**

## 3. 고척 입장 안내

```text
candidate_id: SGC_20260911T004343_0399aa1274
logical_document_id: GOCHEOK_stadium_entry_guide
operation: CREATE
content_hash: 8d5ed80e6efbd51a9b9cf52daabddc154ea06873498fa6bebd6a5da2ad1b6570
as_of: 2026-09-11
source_id: heroes_gocheok_faq
```

후보 본문 핵심:

- 최초 입장 시 음식물 반입이 가능하다.
- 재입장 시 외부 음식 반입은 제한된다.

검수 결과:

- 두 문장 모두 공식 FAQ에 있다.
- 주류, 캔, 용량, 선예매와 연간회원 정보는 제거됐다.
- 음식물 안내와 일부 내용이 겹치지만 entry 문서가 재입장 질문에 독립적으로
  답하는 데 필요한 최소 문장만 유지했다.

권장 결정: **승인**

## 4. KBO 공통 반입 정책

```text
candidate_id: SGC_20260911T005413_5cb4de4620
logical_document_id: KBO_common_stadium_bag_policy
operation: CREATE
content_hash: 600f2e6c42d57e53781d53c6b260b86b788000db8c3df12858d3ffb27ca3b1c0
as_of: 2026-09-11
source_id: kbo_safe_campaign
```

후보가 포함하는 내용:

- 가방 1개는 45cm × 45cm × 20cm까지 허용한다.
- 쇼핑백 1개는 30cm × 손잡이 포함 50cm × 12cm까지 허용한다.
- 기준을 벗어난 가방, 상자, 아이스박스, 돗자리, 휴대용 의자와 간이테이블을
  제한한다.
- 모든 유리병, 총량 1L 초과 PET·알루미늄 캔 음료와 얼린 생수를 제한한다.
- 미개봉 음료는 1인당 PET 1개와 캔 2개까지 허용한다고 안내한다.
- 위험 물품과 경기 진행을 방해하는 물품의 공식 예시를 포함한다.
- 이 규정은 공통 최소 기준이며 구장별 예외가 있을 수 있음을 표시한다.

검수 결과:

- parser가 KBO 페이지 메뉴와 footer를 제외하고 정책·예외 블록만 추출한다.
- 구장 내 매점의 주류 판매량과 판매 종료 시각은 반입 규정이 아니므로
  후보에서 제거됐다.
- `총량 1L`이 단일 용기인지 1인당 합계인지 원문이 명확히 구분하지 않아
  limitation에 남겼다.

권장 결정: **승인**

## 승인 및 실행 결과

2026-09-11 사용자가 네 후보를 승인했고 다음 순서로 로컬에만 적용했다.

1. KBO 공통 반입 정책
2. 고척 음식물 안내
3. 고척 반입 정책
4. 고척 입장 안내

각 후보는 문서 한 건만 임베딩했고, 매 적용 후 고척 대상 평가와 사직 회귀
평가를 실행했다. 네 후보 모두 평가를 통과해 `ready_for_production` 상태다.
재실행 시 모두 `already_applied=true`로 반환되어 중복 문서나 청크가
생기지 않았다.

## 최종 확인

- [x] 네 후보의 문장이 공식 출처 범위 안에 있다.
- [x] food, bag, entry 문서 경계를 수용한다.
- [x] 모호한 용기 표현과 총용량 적용 대상을 limitation으로 두는 데 동의한다.
- [x] `올 시즌부터` 문구를 기준일과 limitation을 함께 표시해 유지한다.
- [x] 네 후보를 승인하고 로컬 임베딩·평가를 실행한다.

로컬 적용 후 상태:

```text
rag_documents=9
rag_chunks=9
ready_for_production=4
rejected=4
completed_local_deployments=4
```

운영 DB에는 아직 승격하지 않았다.
