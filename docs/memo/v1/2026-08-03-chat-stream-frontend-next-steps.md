# Chat Stream Frontend Next Steps

> 작성일: 2026-08-03
> 목적: 다른 컴퓨터에서 MVP1 채팅 스트리밍 연결 작업을 바로 이어가기 위한 현재 상태 정리

## 1. 현재 상태 요약

MVP1의 백엔드/프론트 기본 틀은 다음 상태까지 진행됐다.

```text
POST /api/v1/chat SSE endpoint 구현 완료
guest_id / conversation_id / message request contract 정의
conversation/message 저장 흐름 연결
Tool routing + Tool executor 연결
tool.started / tool.completed / tool.failed event 정의
assistant.delta / assistant.completed event 정의
프론트 Tool card component 분리 완료
프론트에서 /api/v1/chat fetch stream client 추가
프론트에서 SSE event를 message/tool card state에 반영하는 기본 연결 완료
```

최근 관련 커밋:

```text
c4db7a6 feat: connect chat stream in frontend
771fb4a docs: update mvp1 planning status
f3517c8 docs: add mvp2 backend upgrade plan
7967b14 feat: add tool result cards
fb5f13c feat: add streaming chat endpoint
```

현재 worktree는 clean 상태에서 이 메모 작성을 시작했다.

## 2. 주요 변경 파일

백엔드 chat stream:

```text
backend/app/domains/chat/controller/router.py
backend/app/domains/chat/controller/schemas.py
backend/app/domains/chat/service/services.py
backend/app/domains/chat/service/sse.py
backend/app/api/dependencies.py
backend/app/api/v1/router.py
```

프론트 stream 연결:

```text
frontend/src/features/chat-stream/api/stream-chat-message.ts
frontend/src/features/chat-stream/model/guest-session.ts
frontend/src/widgets/chat/ui/chat-panel.tsx
frontend/src/features/send-message/ui/chat-composer.tsx
```

프론트 Tool card:

```text
frontend/src/entities/tool-result/model/types.ts
frontend/src/entities/tool-result/ui/tool-result-card.tsx
frontend/src/entities/tool-result/ui/cards/
```

기획 문서:

```text
docs/planning/001-service-and-mvp.md
docs/planning/002-mvp2-backend-upgrade-plan.md
docs/frontend/mvp-chat-ux-plan.md
```

## 3. 실행 조건

프론트의 기본 백엔드 주소:

```text
http://127.0.0.1:4000
```

다른 주소를 쓰려면 frontend env에 설정한다.

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:4000
```

채팅 테스트에 필요한 조건:

```text
1. backend 실행
2. Supabase/Postgres 실행
3. chat_conversations / chat_messages migration 적용
4. KBO 일정, 구장, RAG 데이터 적재
5. rag_chunks.embedding 값 존재
6. OpenAI API key 설정
7. 날씨 Tool 테스트 시 KMA env 설정
8. frontend 실행
```

프론트 검증 결과:

```text
pnpm lint      통과
pnpm typecheck 통과
pnpm build     통과
```

주의:

```text
마지막 작업 환경에서는 Next dev server를 새로 띄우려 할 때 3001 포트 lock/PID가 남아 있었다.
Next가 PID 5833을 보고했지만 curl 연결은 되지 않았다.
다른 컴퓨터에서는 우선 3001로 실행하고, 포트 충돌이 있으면 다른 포트를 사용한다.
```

## 4. 현재 프론트 동작 흐름

`ChatPanel`이 메시지 상태를 소유한다.

```text
사용자 입력
→ ChatComposer.onSendMessage
→ local user message 추가
→ streamChatMessage() 호출
→ conversation.created 수신 시 conversation_id localStorage 저장
→ message.created 수신 시 backend message id로 local message 교체 또는 assistant message 추가
→ tool.started 수신 시 running Tool card 추가
→ tool.completed 수신 시 같은 tool_call_id card를 completed로 갱신
→ tool.failed 수신 시 같은 tool_call_id card를 failed로 갱신
→ assistant.delta 수신 시 assistant message content 누적
→ assistant.completed 수신 시 assistant message 완료 content 반영
```

localStorage key:

```text
baseball-agent:guest-id
baseball-agent:current-conversation-id
```

## 5. 먼저 테스트할 질문

백엔드와 Supabase가 켜진 뒤 아래 순서로 테스트한다.

```text
다음 주 롯데 경기 알려줘
잠실야구장 위치 알려줘
보크가 뭐야?
```

추가 테스트 후보:

```text
내일 문학구장 날씨 알려줘
이번 주말 롯데 홈경기 예매 방법 알려줘
사직구장 처음 가는데 뭐 챙겨야 해?
```

테스트에서 확인할 것:

```text
conversation.created가 도착하는가
message.created가 user/assistant 각각 도착하는가
tool.started card가 먼저 뜨는가
tool.completed 후 card 내용이 채워지는가
assistant.delta가 말풍선에 누적되는가
새로고침 후 같은 conversation_id로 이어지는가
에러 발생 시 화면에 error message가 보이는가
```

## 6. 바로 다음 작업

우선순위 1:

```text
백엔드 + Supabase + 프론트 실제 실행 후 end-to-end 수동 테스트
```

우선순위 2:

```text
프론트 stream 상태 보강
- 자동 scroll to bottom
- 중복 전송 UX 개선
- 현재 conversation 새로 시작 버튼
- conversation_id가 만료되거나 backend에서 404를 반환할 때 localStorage 정리
```

우선순위 3:

```text
Tool card 실제 데이터 표시 검수
- find_kbo_game
- get_stadium_info
- get_weather_context
- search_ticketing_guide
- search_stadium_guide
- search_baseball_knowledge
```

우선순위 4:

```text
MVP2 검색 품질 개선 착수
- search_baseball_knowledge 평가셋 작성
- semantic search baseline run 저장
- 실패 케이스 확인 후 hybrid search 실험
```

## 7. 참고 문서

```text
docs/planning/001-service-and-mvp.md
docs/planning/002-mvp2-backend-upgrade-plan.md
docs/frontend/mvp-chat-ux-plan.md
blog/2026-08-02-baseball-knowledge-rag-baseline.md
```
