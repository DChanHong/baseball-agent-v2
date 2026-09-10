# Stadium Guide Data

구장 가이드 RAG 후보 데이터와 검색 평가 데이터를 보관한다.

## 구조

```text
data/stadium_guide/
├── sources.json
├── source-registry.schema.json
├── collection_summary.md
├── raw/
├── normalized/
├── embedded_input/
├── evaluation/
│   ├── cases/
│   └── runs/
└── README.md
```

## 주요 파일

```text
sources.json
collection_summary.md
embedded_input/stadium_guide_chunks.jsonl
evaluation/cases/sajik_search_cases.jsonl
```

## 원칙

- 공식 출처가 확인된 데이터만 RAG 후보로 유지한다.
- sources.json에 등록되고 enabled=true인 출처만 수집한다.
- 신규 출처는 배열형 stadium_ids, team_ids와 수집기·parser를 명시한다.
- 기존 단수형 ID는 전환 기간 동안 loader가 읽되 새 출처에는 사용하지 않는다.
- raw snapshot은 원본 보존용이며 직접 수정하지 않는다.
- normalized 문서는 embedding 전 검수 가능한 문서 단위다.
- embedded input은 OpenAI embedding API 호출 전 입력 산출물이다.
