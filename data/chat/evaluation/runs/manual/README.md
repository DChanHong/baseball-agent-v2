# Manual Chat QA Runs

브라우저에서 실제 채팅 흐름을 검증한 milestone 실행 결과를 저장한다.

파일명:

```text
YYYY-MM-DD_HHMMSS_manual-qa-v<n>.json
```

실행 전 질문 세트는 모든 결과를 `not_run`으로 준비할 수 있다. 실행을 시작하면 같은 파일에 관찰값을 기록하고, 마지막에 `summary` 합계를 다시 계산한다.

각 파일은 `../../schemas/manual_chat_qa_run.schema.json`을 만족해야 한다.
