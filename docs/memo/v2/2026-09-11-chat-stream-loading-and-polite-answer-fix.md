# 채팅 로딩 종료와 존댓말 답변 수정

> 작업일: 2026-09-11
> 상태: 구현 및 검증 완료
> 관련 커밋: `d7fd748 fix: finish chat streams with polite answers`

## 발견한 증상

`키움 예매 어디서 하지?`와 같은 질문에서 예매 안내 카드는 표시되지만,
화면의 답변 작성 중 상태가 계속 남는 경우가 있었다.

카드에 표시된 `고척스카이돔 stadium_ticketing_guide 초안`과 서술형 본문은
최종 답변이 아니라 RAG에서 검색한 근거 문서였다. 최종 답변 생성이 끝나지
않아 근거 카드만 보이면서 문서의 서술체가 서비스 답변처럼 보였다.

## 원인

처리 흐름은 다음과 같았다.

```text
예매 안내 RAG 검색 완료
-> tool.completed 이벤트와 근거 카드 표시
-> 최종 답변 LLM 호출 대기
-> assistant.completed 및 done 이벤트 지연
-> 프런트엔드 로딩 상태 유지
```

프런트엔드는 응답 스트림 자체가 닫히는 시점에 주로 로딩을 해제했다.
따라서 완료 이벤트를 받았어도 연결 종료가 늦으면 입력창과 응답 상태가
계속 로딩으로 남을 수 있었다.

답변 생성 프롬프트에도 모든 답변을 `합니다/입니다` 형식으로 작성하라는
명시적인 규칙이 없었다. LLM을 사용하지 않는 기본 답변에도 `있어요`,
`해드릴게요` 같은 해요체가 섞여 있었다.

## 수정 내용

### 프런트엔드 로딩 종료

- `assistant.completed` 이벤트를 받으면 즉시 로딩을 종료한다.
- `done` 이벤트에서도 로딩 상태와 활성 assistant 메시지 ID를 정리한다.
- SSE parser가 `done` 이벤트를 전달한 뒤 응답 읽기를 종료한다.

### 최종 답변 생성 시간 제한

- 최종 답변 LLM 호출에 애플리케이션 수준의 timeout을 적용했다.
- 기본값은 15초이며 `OPENAI_ANSWER_TIMEOUT_SECONDS`로 조정할 수 있다.
- 제한 시간을 넘기거나 호출이 실패하면 근거 기반 기본 답변으로 전환한다.

이 제한은 SDK 내부 timeout이나 재시도 동작과 관계없이 최종 답변 생성
시간의 상한을 보장한다.

### 존댓말 정책

- 모든 최종 답변을 존댓말로 작성한다.
- `합니다`, `입니다`, `확인해 주세요` 형식을 일관되게 사용한다.
- `한다`, `필요하다`와 같은 문서 서술체를 사용자 답변에 사용하지 않는다.
- LLM 호출 실패 시 사용하는 기본 답변도 같은 형식으로 통일한다.

```text
변경 전: 관련 안내 문서 1건을 찾았습니다. 카드에서 확인할 수 있어요.
변경 후: 관련 안내 문서 1건을 찾았습니다. 카드에서 확인해 주세요.
```

## 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `frontend/src/widgets/chat/ui/chat-panel.tsx` | 완료 이벤트 수신 시 로딩과 활성 메시지 상태 정리 |
| `frontend/src/features/chat-stream/api/stream-chat-message.ts` | `done` 이벤트 이후 SSE 읽기 종료 |
| `backend/app/agent/answer_generation_service.py` | 최종 답변 생성 timeout 적용 |
| `backend/app/agent/prompt_assets/answer_generation_policy.md` | 존댓말 답변 규칙 추가 |
| `backend/app/agent/answering.py` | 기본 답변을 격식체로 통일 |
| `backend/app/core/config.py` | 답변 생성 timeout 설정 추가 |
| `backend/.env.example` | timeout 환경변수 예시 추가 |
| `backend/tests/api/test_answer_generation_service.py` | 존댓말 정책과 timeout 테스트 추가 |

## 검증 결과

```text
backend tests: 70 passed
frontend lint: passed
frontend typecheck: passed
changed Python files lint: passed
```

실제 모델 호출이 15초를 넘을 때 명시적인 timeout이 발생하는 것도 확인했다.
서비스에서는 이 예외를 처리해 기본 답변으로 전환하므로 답변 상태가 무기한
남지 않는다.

## 운영 반영 시 확인 사항

이 변경은 DB migration이나 RAG 재임베딩이 필요하지 않다. 운영 서버에
커밋 `d7fd748`을 포함한 백엔드와 프런트엔드 코드를 배포하면 적용된다.

배포 후 `키움 예매 어디서 하지?` 질문으로 다음 항목을 확인한다.

1. 예매 안내 근거 카드가 표시된다.
2. 최종 답변이 `합니다/입니다` 형식으로 표시된다.
3. 답변 완료 후 로딩 표시가 사라진다.
4. 입력창이 다시 활성화된다.
5. 모델 응답이 늦거나 실패해도 기본 답변으로 정상 종료된다.
