# Security Review Workflow

## 1. 범위 잡기

- 전체 리뷰인지 diff 리뷰인지 확인한다.
- 관련 파일과 data flow를 먼저 나열한다.
- 변경된 dependency와 config가 있으면 별도 항목으로 둔다.

## 2. Trust Boundary 표시

다음 값을 untrusted로 표시한다.

- 사용자 입력
- URL/search parameter
- localStorage/sessionStorage
- backend JSON
- SSE stream event
- LLM 응답
- tool result
- citation/source URL

## 3. Data Flow 따라가기

- untrusted data가 어디서 들어오는지 본다.
- parsing/validation/type narrowing 위치를 확인한다.
- 저장 위치를 확인한다.
- 렌더링 위치를 확인한다.
- 링크, HTML, markdown, image, script처럼 browser가 해석하는 sink로 가는지 확인한다.

## 4. Finding 작성

finding은 다음 형태로 쓴다.

```text
[Severity] 제목
위치: path
분류: XSS | secret exposure | auth/session | storage | unsafe link | data validation | SSE/API | dependency | insecure default
영향: ...
근거: ...
수정: ...
확신도: high | medium | low
```

## 5. False Positive 확인

- 공격자가 해당 data를 제어할 수 있는가?
- 실제 sink까지 도달하는가?
- framework가 자동 escape하는가?
- backend나 schema가 이미 막고 있는가?
- 그래도 defense-in-depth 수정이 가치 있는가?

## 6. 검증

기본 검증:

```bash
pnpm lint
pnpm typecheck
```

dependency 변경이 있으면 추가로 검토한다.

```bash
pnpm audit
```

Semgrep이 필요한 경우에는 무작정 실행보다 먼저 rule 목적을 정한다.

## 7. 리뷰 결과 정리

- finding이 있으면 심각도 순으로 정리한다.
- finding이 없으면 "현재 확인 범위에서는 발견 없음"이라고 명시한다.
- scanner를 실행하지 못했거나 backend 확인이 필요한 경우 test gap으로 남긴다.
