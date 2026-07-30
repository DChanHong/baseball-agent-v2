# KBO Schedule Data

KBO 경기 일정 조회와 `find_kbo_game` Tool 평가에 필요한 데이터를 보관한다.

## 구조

```text
data/kbo_schedule/
├── raw/
│   └── 2026/
├── processed/
├── evaluation/
│   ├── cases/
│   └── runs/
└── README.md
```

## 주요 파일

```text
raw/2026/*.json
processed/kbo_schedule_2026_normalized.json
evaluation/cases/find_kbo_game_cases.jsonl
```
