# Stadium Guide Retrieval Evaluation

구장 가이드 RAG 검색 품질을 확인하기 위한 평가 데이터다.

기존 회귀 대상은 `SAJIK`이며, `gocheok_food_search_cases.jsonl`은
고척의 음식물·재입장·용기·주류 질문과 구장별 정책 우선순위를 검증한다.
목표는 embedding vector 자체가 아니라 사용자 질문에서 기대한
`document_type`이 검색 결과 상위에 나오는지 확인하는 것이다.

## 기준

초기 평가는 다음 두 기준을 기록한다.

```text
Top-1 hit: 첫 번째 검색 결과의 document_type이 expected_document_type과 일치하는가
Top-3 hit: 상위 3개 검색 결과 안에 expected_document_type이 포함되는가
```

## 주의

- `negative` 케이스는 검색 품질보다 앞단의 stadium/team 추출 또는 clarification 필요성을 확인하기 위한 데이터다.
- 현재 SAJIK만 embedding되어 있으므로, 다른 구장 질문은 실제 서비스에서는 검색 전에 구장 불일치를 처리해야 한다.
- Phase 3 후보 평가는 변경 문서 유형의 고척 case와 사직 회귀 case를 함께 실행한다.
- 고척 대상 결과는 출처 URL과 기준일(`as_of`)이 있어야 통과한다.
