# Backend 요청 흐름 따라읽기

> 목적: 파일을 랜덤하게 열지 않고 실제 요청 흐름대로 코드를 읽는다.

## 1. 전체 router 연결 흐름

모든 API 요청은 다음 연결을 거친다.

```text
backend/app/main.py
-> app.include_router(api_router)

backend/app/api/router.py
-> api_router.include_router(v1_router, prefix="/api/v1")

backend/app/api/v1/router.py
-> auth_router
-> chat_router
-> baseball_router
-> conversation_router
```

따라서 `baseball/controller/router.py`에 `prefix="/games"`가 있으면 실제 URL은 다음과 같다.

```text
/api/v1/games
```

## 2. `GET /api/v1/games`

가장 먼저 읽기 좋은 흐름이다.

### 2.1 Endpoint

파일:

```text
backend/app/domains/baseball/controller/router.py
```

핵심:

```python
@router.get("", response_model=list[KboGameResponse])
async def list_kbo_games(...):
```

이 함수가 query parameter를 받는다.

입력 예:

```text
GET /api/v1/games?team_id=LOTTE&date=2026-08-24
```

### 2.2 Dependency 생성

같은 router 파일에 다음 타입 alias가 있다.

```python
ListKboGamesServiceDependency = Annotated[
    ListKboGamesService,
    Depends(get_list_kbo_games_service),
]
```

FastAPI는 endpoint 실행 전에 `get_list_kbo_games_service()`를 호출한다.

파일:

```text
backend/app/api/dependencies.py
```

흐름:

```text
get_db_session()
-> AsyncSession
-> SqlAlchemyKboGameRepository(session)
-> ListKboGamesService(repository)
```

### 2.3 Request 값을 service query로 변환

controller에서 다음 객체를 만든다.

```python
query = ListKboGamesQuery(
    team_id=team_id,
    date=date_,
    date_from=date_from,
    date_to=date_to,
)
```

파일:

```text
backend/app/domains/baseball/service/dto.py
```

`ListKboGamesQuery.__post_init__()`는 다음 규칙을 검증한다.

- `team_id`는 빈 문자열이면 안 된다.
- `date`와 `date_from/date_to`를 함께 쓰면 안 된다.
- `date_from`이 `date_to`보다 늦으면 안 된다.

### 2.4 Service 실행

파일:

```text
backend/app/domains/baseball/service/services.py
```

흐름:

```text
ListKboGamesService.execute(query)
-> repository.list_games(...)
-> KboGameResultDto.from_entity(...)
```

service는 SQLAlchemy 문법을 모른다. `KboGameRepository`라는 저장소 역할만 알고 호출한다.

### 2.5 Repository 조회

파일:

```text
backend/app/domains/baseball/infrastructure/repositories.py
```

흐름:

```text
select(KboGameModel)
-> where(team/date 조건)
-> order_by(...)
-> session.execute(statement)
-> result.scalars().all()
```

이 파일은 DB 구현 세부사항을 안다.

### 2.6 ORM model과 domain entity 변환

파일:

```text
backend/app/domains/baseball/infrastructure/mappers.py
```

흐름:

```text
KboGameModel
-> KboGameMapper.to_domain()
-> KboGame
```

`KboGameModel`은 DB table 모양이고, `KboGame`은 domain에서 쓰는 순수 객체다.

### 2.7 Response 변환

controller로 돌아와서 다음 변환을 한다.

```python
return [KboGameResponse.model_validate(result) for result in results]
```

파일:

```text
backend/app/domains/baseball/controller/schemas.py
```

최종적으로 FastAPI가 `KboGameResponse` list를 JSON으로 변환한다.

## 3. `GET /api/v1/conversations`

인증된 사용자 context와 repository 조회를 같이 볼 수 있는 흐름이다.

### 3.1 Endpoint

파일:

```text
backend/app/domains/conversation/controller/router.py
```

핵심 parameter:

```python
service: ListConversationsServiceDependency
current_user: CurrentUserDependency
limit: Annotated[int, Query(ge=1, le=100)] = 50
offset: Annotated[int, Query(ge=0)] = 0
```

여기서 `current_user`는 client가 직접 보내는 JSON body가 아니다. FastAPI dependency가 cookie에서 access token을 읽고 사용자 정보를 resolve한다.

### 3.2 Current user dependency

파일:

```text
backend/app/api/dependencies.py
```

흐름:

```text
request.cookies[auth_access_cookie_name]
-> AuthSessionService.get_current_user(access_token)
-> CurrentUserDto
```

access token이 없거나 유효하지 않으면 `HTTP_401_UNAUTHORIZED`가 발생한다.

### 3.3 Service query

controller는 현재 사용자 id를 query에 담는다.

```python
query = ListConversationsQuery(
    user_profile_id=current_user.id,
    limit=limit,
    offset=offset,
)
```

이 구조 덕분에 client가 다른 사용자의 id를 query parameter로 넣어도 사용되지 않는다.

### 3.4 Repository 조회

파일:

```text
backend/app/domains/conversation/infrastructure/repositories.py
```

`list_by_user_profile_id(...)`가 로그인 사용자의 대화방만 조회한다.

## 4. `GET /api/v1/conversations/{id}/messages`

소유권 확인 흐름을 보기 좋다.

파일:

```text
backend/app/domains/conversation/service/services.py
```

핵심 흐름:

```text
conversation_repository.find_by_id(conversation_id)
-> 없으면 ConversationNotFoundError
-> conversation.user_profile_id != current_user.id 이면 ConversationAccessDeniedError
-> message_repository.list_by_conversation_id(...)
```

controller는 domain exception을 HTTP 응답으로 바꾼다.

```text
ConversationNotFoundError -> 404 conversation_not_found
ConversationAccessDeniedError -> 403 conversation_access_denied
```

학습 포인트:

- 보안 규칙은 controller의 query parameter가 아니라 service에서 확인한다.
- repository는 DB 조회만 담당하고, “이 사용자가 읽어도 되는가” 같은 use case 판단은 service가 담당한다.

## 5. `POST /api/v1/chat`

가장 복잡한 흐름이다. 처음에는 `ChatStreamService._stream_inner()`의 큰 단계만 따라간다.

### 5.1 Endpoint

파일:

```text
backend/app/domains/chat/controller/router.py
```

핵심:

```python
@router.post("")
async def stream_chat(...) -> StreamingResponse:
```

반환 타입이 일반 JSON이 아니라 `StreamingResponse`다.

```python
return StreamingResponse(
    service.stream(request, current_user=current_user),
    media_type="text/event-stream",
)
```

### 5.2 ChatStreamService 생성

파일:

```text
backend/app/api/dependencies.py
```

흐름:

```text
get_chat_stream_service(session)
-> SqlAlchemyConversationRepository(session)
-> SqlAlchemyMessageRepository(session)
-> ToolRoutingService()
-> AgentToolExecutor(...)
-> ChatStreamService(...)
```

`AgentToolExecutor` 안에는 baseball tool handler들이 들어간다.

### 5.3 Stream 내부 단계

파일:

```text
backend/app/domains/chat/service/services.py
```

큰 흐름:

```text
1. 대화방을 찾거나 새로 만든다.
2. user message를 DB에 저장한다.
3. assistant placeholder message를 DB에 저장한다.
4. agent graph를 실행한다.
5. tool started/completed/failed event를 SSE로 보낸다.
6. 최종 assistant 답변을 delta chunk로 보낸다.
7. assistant message와 conversation metadata를 저장한다.
8. assistant.completed, conversation.updated, done event를 보낸다.
```

SSE event 예:

```text
conversation.created
message.created
tool.started
tool.completed
assistant.delta
assistant.completed
conversation.updated
done
```

### 5.4 Agent graph

파일:

```text
backend/app/agent/graph.py
```

LangGraph node:

```text
route
prepare_tool
tool_execute
state_update
answer_generate
```

`route`에서 LLM이 `ToolRoutingDecision`을 만든다.

```text
사용자 질문
-> ToolRoutingService.execute()
-> ToolRoutingDecision
```

`ToolRoutingDecision.should_call_tool`이 true이면 tool을 실행한다. false이면 바로 답변 생성으로 간다.

### 5.5 Routing service

파일:

```text
backend/app/agent/routing_service.py
```

핵심:

```text
ChatPromptTemplate
-> ChatOpenAI
-> with_structured_output(ToolRoutingDecision)
-> chain.ainvoke(...)
```

즉, LLM에게 자유 텍스트를 받는 것이 아니라 `ToolRoutingDecision` Pydantic schema에 맞는 구조화된 결정을 받는다.

### 5.6 Tool executor

파일:

```text
backend/app/agent/tool_executor.py
backend/app/agent/tool_registry.py
```

흐름:

```text
ToolRoutingDecision.tool_name
-> get_agent_tool_spec(tool_name)
-> decision.args 타입 검증
-> tool input schema로 변환
-> handler.execute(tool_input)
```

tool 이름이 직접 `if/elif`로 길게 나열되지 않고, `tool_registry.py`의 spec을 통해 연결된다.

## 6. `GET /api/v1/auth/me`

인증 session 읽기 흐름이다.

### 6.1 Endpoint

파일:

```text
backend/app/domains/auth/controller/router.py
```

흐름:

```text
request.cookies[auth_access_cookie_name]
-> AuthSessionService.get_current_user(access_token)
-> to_current_user_response(user)
```

### 6.2 Service

파일:

```text
backend/app/domains/auth/service/services.py
```

확인할 것:

- Supabase access token을 어떻게 검증하는가?
- Supabase user와 application user profile을 어떻게 연결하는가?
- profile이 없을 때 생성하는가, 오류를 내는가?

### 6.3 Infrastructure

파일:

```text
backend/app/domains/auth/infrastructure/supabase_auth_client.py
backend/app/domains/auth/infrastructure/repositories.py
```

역할:

- Supabase Auth HTTP API 호출
- `user_profiles` table 조회/저장

## 7. Tool 하나를 따라읽는 방법

예시: `find_kbo_game`

파일:

```text
backend/app/domains/baseball/tool/find_kbo_game/schemas.py
backend/app/domains/baseball/tool/find_kbo_game/handler.py
backend/app/api/dependencies.py
backend/app/agent/tool_registry.py
backend/app/agent/tool_executor.py
```

읽는 순서:

```text
1. routing_schemas.py에서 FindKboGameRoutingArgs 확인
2. tool_registry.py에서 find_kbo_game spec 확인
3. schemas.py에서 FindKboGameToolInput/Output 확인
4. dependencies.py에서 handler 생성 방식 확인
5. handler.py에서 실제 execute 흐름 확인
6. baseball service/repository로 이어지는지 확인
```

RAG tool은 여기에 `retriever.py`를 추가로 읽는다.

## 8. 코드 읽기 체크리스트

새 endpoint나 tool을 볼 때마다 아래 순서로 읽으면 된다.

1. 최종 URL과 HTTP method를 찾는다.
2. router function parameter를 본다.
3. `Depends(...)`로 들어오는 service/handler를 찾는다.
4. request schema와 service DTO를 구분한다.
5. service가 어떤 repository/client/tool을 호출하는지 본다.
6. DB 접근이면 infrastructure repository와 model을 본다.
7. 외부 API 접근이면 infrastructure client를 본다.
8. 결과가 어떤 DTO/schema로 변환되어 반환되는지 본다.
9. 예외가 어디에서 HTTP status로 변환되는지 본다.
10. 관련 테스트가 있는지 `tests/api/`에서 찾는다.

