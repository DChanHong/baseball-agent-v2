# Manual QA Candidates

실패 또는 애매한 QA 결과 중 사람 검토가 필요한 항목을 보관한다.

첫 candidate가 발생하면 다음 파일을 만든다.

```text
manual_chat_qa_candidates.jsonl
```

각 줄은 `../schemas/manual_chat_qa_candidate.schema.json`을 만족해야 한다. 관찰하지 않은 실패를 예시 데이터로 만들지 않는다.
