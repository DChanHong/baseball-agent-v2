# Data

프로젝트 데이터는 도메인별로 관리한다.

```text
data/
├── kbo_schedule/
└── stadium_guide/
```

## 원칙

- `raw/`는 원본 수집 데이터를 보관한다.
- `processed/` 또는 `normalized/`는 서비스와 스크립트가 읽기 쉬운 정규화 데이터를 보관한다.
- `evaluation/cases/`는 사람이 검토 가능한 평가 데이터셋을 보관한다.
- `evaluation/runs/`는 평가 실행 결과를 보관한다.
- API key, 사용자 개인정보, 실제 사용자 대화 전문은 저장하지 않는다.
