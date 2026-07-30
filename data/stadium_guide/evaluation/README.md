# Stadium Guide Retrieval Evaluation

구장 가이드 RAG 검색 품질을 확인하기 위한 평가 데이터다.

현재 첫 대상은 `SAJIK`이며, 목표는 embedding vector 자체가 아니라 사용자 질문에서 기대한 `document_type`이 검색 결과 상위에 나오는지 확인하는 것이다.

## 기준

초기 평가는 다음 두 기준을 기록한다.

```text
Top-1 hit: 첫 번째 검색 결과의 document_type이 expected_document_type과 일치하는가
Top-3 hit: 상위 3개 검색 결과 안에 expected_document_type이 포함되는가
```

## 주의

- `negative` 케이스는 검색 품질보다 앞단의 stadium/team 추출 또는 clarification 필요성을 확인하기 위한 데이터다.
- 현재 SAJIK만 embedding되어 있으므로, 다른 구장 질문은 실제 서비스에서는 검색 전에 구장 불일치를 처리해야 한다.
