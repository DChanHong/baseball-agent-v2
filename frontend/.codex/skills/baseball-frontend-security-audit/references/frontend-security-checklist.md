# Frontend Security Checklist

## Trust Boundary

- 사용자 입력, URL parameter, localStorage/sessionStorage, backend 응답, SSE event, LLM 응답, tool result, citation/source data는 모두 untrusted data로 본다.
- UI 표시용 데이터와 권한 판단용 데이터를 분리한다.
- client에서 만든 id는 사용자 경험용 identifier일 수 있지만 권한의 단독 근거가 되면 안 된다.

## XSS와 Content Rendering

- `dangerouslySetInnerHTML` 사용은 기본적으로 금지한다. 꼭 필요하면 sanitize 정책과 허용 tag/attribute를 명시한다.
- LLM 응답, tool result content, citation snippet, source title은 plain text로 렌더링한다.
- Markdown rendering을 도입하면 HTML passthrough, link protocol, image URL, code highlighting plugin을 별도 검토한다.
- URL은 `http:`/`https:` 등 허용 protocol만 통과시킨다. `javascript:`, `data:`, control character가 섞인 URL을 거부한다.

## Link Safety

- 외부 링크는 새 탭이면 `rel="noopener noreferrer"`를 사용한다.
- 출처 URL은 표시 text와 실제 href가 다를 수 있으므로 둘 다 untrusted로 본다.
- source/citation link는 공식 출처 표시와 클릭 가능한 URL을 분리해 검증 가능성을 높인다.

## Secret과 Environment

- `NEXT_PUBLIC_*`에는 공개 가능한 값만 둔다.
- API key, service role key, access token, refresh token은 client bundle에 들어가면 안 된다.
- secret 값은 로그, error message, URL query, localStorage/sessionStorage에 남기지 않는다.
- `.env.example`은 변수 이름과 용도만 포함하고 실제 값이나 유추 가능한 token을 포함하지 않는다.

## Auth, Guest Session, Storage

- guest id, conversation id, profile state는 권한 검증의 증거가 아니라 UI/session continuity 값으로 취급한다.
- localStorage/sessionStorage에는 secret, 민감한 사용자 정보, 실제 사용자 대화 전문을 저장하지 않는다.
- storage schema는 version을 두고, 오래된 값이 parsing 실패를 일으키지 않게 한다.
- logout 또는 session reset 흐름이 생기면 storage cleanup을 같이 확인한다.

## API, SSE, Streaming

- SSE parser는 event type과 payload shape를 명시적으로 검증한다.
- malformed event, partial chunk, duplicated event, unknown type, abort, retry 상황을 확인한다.
- 에러 메시지는 사용자에게 필요한 수준으로만 보여주고 내부 stack/secret/request detail을 노출하지 않는다.
- backend payload는 zod schema 또는 안전한 type narrowing 이후 렌더링한다.
- optimistic UI는 backend 확정 결과와 불일치할 때 되돌릴 수 있어야 한다.

## Dependency와 Supply Chain

- `package.json`, `pnpm-lock.yaml` 변경은 별도 리뷰 대상이다.
- 새 dependency는 maintainer, install script, transitive dependency, bundle impact, 대체 가능성을 확인한다.
- `postinstall`, `prepare`, `preinstall` script가 추가되면 높은 위험으로 본다.
- security scanner 결과가 없어도 lockfile diff에서 갑작스러운 dependency 폭증을 확인한다.

## Browser API와 Client Footguns

- `window`, `document`, `navigator`, clipboard, geolocation, notification, service worker 사용은 사용자 동의와 fallback을 확인한다.
- global event listener는 cleanup을 보장한다.
- cross-tab storage event를 사용하면 stale state와 race condition을 확인한다.
- iframe, postMessage, worker를 도입하면 origin 검증을 명시한다.

## Insecure Defaults

- 개발 편의용 fallback이 production에서도 동작하지 않게 한다.
- validation 실패 시 "대충 표시"보다 안전한 empty/error state로 간다.
- network 실패 시 무한 retry, 중복 요청, stale sensitive data 표시가 없는지 확인한다.
- source가 없거나 기준 시점이 없는 tool result는 신뢰도가 낮다는 UI를 제공한다.
