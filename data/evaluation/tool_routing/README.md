# Tool Routing Evaluation

이 폴더는 LLM이 사용자 질문을 보고 tool 호출 여부와 tool 입력 파라미터를 올바르게 결정하는지 평가하기 위한 데이터셋을 보관한다.

## 현재 데이터셋

```text
find_kbo_game_cases.jsonl
```

평가 대상:

- 질문이 KBO 야구 서비스 범위 안인지
- `find_kbo_game` tool을 호출해야 하는지
- `team_id`를 올바르게 추출했는지
- `date`, `date_from`, `date_to`를 올바르게 추출했는지
- 팀 정보가 부족할 때 되묻기를 선택했는지
- 현재 tool로 처리하기 어려운 질문을 분리했는지

## JSONL 필드

각 줄은 하나의 평가 케이스다.

```json
{
  "id": "fg_001",
  "input": "오늘 롯데 경기 있어?",
  "user_context": {
    "auth_status": "authenticated",
    "favorite_team_id": null,
    "today": "2026-07-28",
    "timezone": "Asia/Seoul"
  },
  "expected": {
    "is_in_scope": true,
    "should_call_tool": true,
    "tool_name": "find_kbo_game",
    "args": {
      "team_id": "LOTTE",
      "date": "2026-07-28",
      "date_from": null,
      "date_to": null
    },
    "needs_clarification": false,
    "clarification_reason": null,
    "unsupported_reason": null
  }
}
```
