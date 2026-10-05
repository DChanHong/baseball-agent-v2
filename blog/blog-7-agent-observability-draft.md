# [AI Agent] 답변이 느린 이유를 찾기: 최소 Observability 구현

> 상태: 구현과 합성 테스트 기반 초안
> 작성일: 2026-10-05
> 실제 서비스 latency 집계와 브라우저 QA 사례는 후속 실행 후 추가한다.

채팅 로딩과 답변 생성 timeout을 고친 뒤, 다음 질문이 남았다.
응답이 늦어졌을 때 routing, 검색, 최종 답변 생성 중 어디에서 시간을 썼는가?

기존에도 각 모듈의 로그와 Tool card가 있었다. 하지만 서로 다른 요청이
동시에 실행되면 로그 순서만으로 같은 질문의 처리 과정을 묶기 어려웠다.
그래서 다음 기능을 늘리기 전에 실행 한 번을 연결하는 작은 trace를 만들었다.

## 1. 처음부터 관측 서비스를 붙이지 않은 이유

첫 범위는 graph 실행 하나를 설명하는 것이다. Python 표준 logging에
`agent_trace` JSON 이벤트를 추가하고, 같은 실행의 이벤트에 임의 trace ID를
붙였다. 외부 수집 서비스와 별도 DB table은 추가하지 않았다.

이 ID를 기존 assistant metadata에도 남겨 답변과 실행 로그를 연결했다.
사용자 ID나 질문 원문을 trace ID 대신 사용하지 않았다.

## 2. 무엇을 측정했는가

routing, Tool 실행, embedding, retrieval, answer와 answer LLM 호출의 시작·종료를
기록했다. 시간은 monotonic clock으로 측정하고 이벤트 시각은 UTC로 남겼다.

검색 결과에서는 chunk ID, distance, 결과 수를 기록했다. 이 정보는 검색
노이즈나 빈 결과를 확인하는 데 사용한다. 실제 query나 검색 문서 본문은
새 trace에 넣지 않았다.

Tool 시간에는 embedding과 검색 시간이 포함된다. answer 시간에도 모델 호출
시간이 포함된다. 이 값을 전부 더하면 중복 계산이 된다.

## 3. 완료와 성공을 구분하기

답변 모델이 timeout을 넘기면 기존 기본 답변으로 전환한다. 사용자는 응답을
받으므로 graph 실행은 완료됐지만, 모델 기반 답변 생성은 실패한 것이다.

따라서 `turn.completed`만 보지 않고 `answer_source=fallback`과
`fallback_reason=TimeoutError`를 함께 본다. Tool 예외 후 기본 답변으로
종료한 경우도 별도로 구분한다.

빈 검색도 비슷하다. 검색 실행 자체는 정상 종료됐지만 결과 수가 0일 수
있다. 또 결과가 있다는 사실만으로 질문에 충분히 답할 수 있다고 볼 수
없다. 검색의 결과 존재 여부와 최종 답변의 answerability를 구분했다.

## 4. 동시 실행과 개인정보

LangGraph는 node를 비동기 task에서 실행한다. trace ID는 graph state로 전달하고,
node 실행 안에서 ContextVar를 설정한 뒤 복원했다. 서로 다른 요청을
공유 mutable 변수 하나로 구분하지 않도록 했다.

새 trace에는 질문·답변·prompt·Tool payload 전문과 인증값을 넣지 않는다.
예외도 메시지 대신 타입만 기록한다. 이 정책은 새 trace의 범위이며 기존
HTTP body logging이나 exception logger 전체를 정비했다는 뜻은 아니다.

## 5. 무엇을 검증했는가

합성 테스트로 정상 RAG, 빈 검색, Tool 실패, 답변 timeout, 무도구 응답,
routing 실패를 검증했다. 동시 실행에서 ID가 섞이지 않는지와 consumer가
stream을 닫았을 때 중단 이벤트가 남는지도 확인했다.

질문·근거·답변·예외에 같은 합성 비공개 문자열을 넣고 새 trace JSON에는
그 문자열이 없는지 검사했다. 전체 backend 테스트는 78개가 통과했다.

이는 실제 모델·운영 DB를 사용한 응답 속도 측정이 아니다. 지금 확보한
것은 이후 성능과 실패를 측정할 수 있는 구조다.

## 6. 다음 실행에서 확인할 것

기존 QA 질문을 같은 조건으로 실행해 단계별 시간과 fallback 빈도를 모은다.
그 결과를 평가 run에 연결하고, 실제 실패가 검색에 집중되는지 복합 질문
처리에 집중되는지 확인한 뒤 다음 개발 범위를 정한다.

현재 trace는 graph에 한정된다. HTTP 처리, 답변 DB 저장과 SSE 전송 실패는
추가 계측이 필요하다. token usage와 운영 로그 보존 정책도 후속 범위다.
