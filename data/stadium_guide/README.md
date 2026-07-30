# Stadium Guide Data

구장 가이드 RAG 후보 데이터와 검색 평가 데이터를 보관한다.

## 구조

```text
data/stadium_guide/
├── sources.json
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
- raw snapshot은 원본 보존용이며 직접 수정하지 않는다.
- normalized 문서는 embedding 전 검수 가능한 문서 단위다.
- embedded input은 OpenAI embedding API 호출 전 입력 산출물이다.
