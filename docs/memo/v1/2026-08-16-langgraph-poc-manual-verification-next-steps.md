# LangGraph PoC Manual Verification Next Steps

> 작성일: 2026-08-16
> 목적: LangGraph 1차 PoC 수동 검증 결과, 런타임 수정 내용, 다음 작업 후보를 기록한다.

## 1. 수동 검증 결과

브라우저에서 로그인 후 같은 대화창에서 아래 흐름을 확인했다.

```text
사용자: 롯데 오늘 야구 일정 알려줘
응답: 경기 일정을 조회했습니다. 조건에 맞는 경기는 총 1건입니다.

Tool card:
- 경기: NC vs 롯데
- 구장: 사직
- 날짜: 2026-08-16
- 상태: scheduled

사용자: 어디서 경기하는거지?
응답: 직전 조회한 NC vs 롯데 경기는 사직에서 열립니다.
```

확인된 동작:

- 첫 턴에서 `find_kbo_game` tool이 호출된다.
- 단일 경기 결과가 `conversation.metadata.agent_context.selected_game`으로 저장된다.
- 같은 `conversation_id`의 다음 턴에서 장소 후속 질문은 tool 재호출 없이 저장된 `selected_game.stadium_name`으로 답한다.
- 따라서 1차 PoC 목표였던 "텍스트 기반 직전 경기 context 연결"은 통과로 본다.

## 2. 발견한 런타임 이슈와 수정

### LangChain prompt template parsing

증상:

```text
ValueError: Invalid format specifier in f-string template. Nested replacement fields are not allowed.
```

원인:

- `ChatPromptTemplate.from_messages()`에 시스템 프롬프트를 문자열 tuple로 넘기고 있었다.
- 시스템 프롬프트 안의 few-shot JSON 예시 `{...}`를 LangChain이 f-string template 변수로 해석했다.

수정:

- `backend/app/agent/routing_service.py`
- 시스템 프롬프트를 `SystemMessage(content=...)`로 감싸 template parsing 대상에서 제외했다.

검증:

```bash
cd backend
uv run python -c 'from app.agent.routing_service import ToolRoutingService; ToolRoutingService(); print("ok")'
uv run pytest tests/api/test_tool_routing_service.py tests/api/test_chat_auth_owner.py
```

결과:

```text
ok
4 passed
```

## 3. 로컬 데이터 이슈

처음 수동 테스트에서 "롯데 오늘 야구 일정 알려줘"가 0건으로 나왔다.

원인:

- `public.kbo_games` 테이블이 비어 있었다.
- repo의 정규화 파일에는 `2026-08-16 NC vs 롯데 @ 사직` 경기가 존재했다.

조치:

```bash
cd backend
uv run python scripts/import_kbo_schedule.py \
  --file ../data/kbo_schedule/processed/kbo_schedule_2026_normalized.json
```

결과:

```text
inserted=675
```

DB 확인:

```text
min_date: 2026-03-28
max_date: 2026-09-06
total: 675

2026-08-16 18:00 NC vs 롯데, 사직, scheduled
```

주의:

- 위 조치는 로컬 DB 데이터 적재이며 Git 커밋 대상 파일 변경은 아니다.
- 다른 개발자가 `supabase db reset`을 하면 다시 import가 필요할 수 있다.

## 4. 다음 작업 후보

### 사용자 답변 품질 개선

- `scheduled`를 사용자 표시용 `예정`으로 변환한다.
- "경기 일정을 조회했습니다. 조건에 맞는 경기는 총 1건입니다."를 더 자연스럽게 바꾼다.
- 단일 경기일 때 assistant text에도 경기/시간/구장을 간단히 포함한다.

예:

```text
오늘 롯데 경기는 18:00 사직에서 NC와 예정되어 있습니다.
```

### 후속 질문 범위 확장

현재 graph direct answer는 장소 질문 중심이다.

추가 후보:

- "몇 시야?"
- "상대가 누구야?"
- "홈 경기야?"
- "상태가 뭐야?"
- "오늘 취소됐어?"

대상 파일:

- `backend/app/agent/answering.py`
- `backend/app/agent/graph.py`
- `backend/tests/api/test_chat_auth_owner.py`

### Context 초기화/갱신 정책

현재는 단일 `find_kbo_game` 결과가 있으면 `selected_game`을 덮어쓴다.

정해야 할 것:

- 여러 경기 결과가 나왔을 때 어떤 경기까지 context로 저장할지
- 새 팀/새 날짜 질문이 들어왔을 때 이전 context를 언제 폐기할지
- "첫 번째 경기", "두 번째 경기" 같은 선택 발화를 지원할지

### 로컬 seed 편의성

수동 QA 전에 일정 데이터가 비어 있으면 테스트가 어긋난다.

개선 후보:

- README 또는 memo에 `import_kbo_schedule.py` 실행 명령을 명시한다.
- `supabase/seed.sql` 또는 별도 seed flow에 2026 normalized schedule import를 연결할지 결정한다.
- `kbo_games`가 비어 있을 때 개발 환경에서 명확한 경고 로그를 남긴다.

## 5. 재현용 질문 목록

핵심 흐름:

```text
롯데 오늘 야구 일정 알려줘
어디서 경기하는거지?
```

추가 장소 후속 질문:

```text
어디서 해?
경기장은 어디야?
그 경기 어디서 하는데?
거기 구장이 어디야?
```

아직 개선 대상:

```text
몇 시 경기야?
상대가 누구야?
홈 경기야?
```
