# Evaluation Runs

이 폴더는 평가 실행 결과를 저장한다.

실행 결과 파일명은 다음 형식을 권장한다.

```text
YYYY-MM-DD_<model>_<prompt-version>.json
```

예:

```text
data/kbo_schedule/evaluation/runs/tool_routing/find_kbo_game/2026-07-28_gpt-5-mini_baseline-v1.json
```

실행 결과에는 최소한 다음 정보를 포함한다.

- dataset path
- model
- prompt version
- run timestamp
- total cases
- tool call accuracy
- parameter accuracy
- failed case ids
