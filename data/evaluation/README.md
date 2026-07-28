# Evaluation Data

이 폴더는 LLM, prompt, tool routing, 답변 품질을 지속적으로 평가하기 위한 데이터와 실행 결과를 보관한다.

## 구조

```text
data/evaluation/
├── tool_routing/
│   └── find_kbo_game_cases.jsonl
├── answer_quality/
└── runs/
```

## 원칙

- `backend/tests`는 코드 회귀 테스트를 담당한다.
- `data/evaluation`은 모델과 prompt 품질 평가를 담당한다.
- 데이터셋은 사람이 검토 가능한 JSONL 형식으로 관리한다.
- 평가 실행 결과는 `runs/` 아래에 모델명, prompt 버전, 실행일과 함께 저장한다.
- API key, 사용자 개인정보, 실제 사용자 대화 전문은 저장하지 않는다.
