# 실제 채팅 API·DB·RAGAS E2E와 첫 서비스 baseline

> 실행일: 2026-10-06 (Asia/Seoul)
> 구현 revision: `805fb31`
> 결과: 실제 로컬 E2E 검증·초기 RAG 3개 baseline 측정 완료. 서비스 품질 전 항목 통과를 뜻하지 않는다.

실제 Supabase Auth, PostgreSQL/pgvector, 채팅 HTTP API, OpenAI 검색 embedding·routing·답변 생성, SSE 후 온라인 Faithfulness를 함께 실행했다. Next.js 화면에서는 기존 smoke 9개를 입력하고 완료·로딩 해제와 DB 답변 재표시를 확인했다. RAG reference는 독립 공식 원문을 Codex가 검수했다. **사람이 승인한 정답셋은 아니며** 파일에 `human_reviewed=false`와 실제 검수 주체를 명시했다.

## 실행과 환경 복구

- 꺼져 있던 Docker Desktop을 시작해 기존 Supabase 컨테이너·볼륨을 복구했다.
- 초기 DB에는 경기 782건과 embedding이 있는 RAG chunk 72건이 있었다. 실제 사용자 레코드나 대화 내용을 읽어 평가에 사용하지 않았다.
- 기존 migration `20260909090000_refresh_stadium_profiles`와 `20260910090000_add_stadium_guide_revision_pipeline`이 미적용이었다. 현재 검색에 필요한 `rag_documents.is_active`, `logical_document_id`, `legacy_unreviewed` 컬럼이 없어 구장·예매 검색이 실패했다.
- 두 SQL 내용을 확인하고 `supabase migration up --local`로 적용했다. 구장 주소와 revision 상태를 기존 저장소 정의에 맞췄다. RAG 본문·embedding을 새 정답에 맞춰 수정하지 않았다.
- 합성 Auth 계정을 별도로 생성하고 실제 password session과 profile을 사용했다. API 인증 의존성을 override하지 않았다. UI용 임시 서버에는 같은 유효 session의 HttpOnly cookie를 발급하는 로컬 경로를 추가했다. Google OAuth 화면 자체의 테스트는 범위에 포함하지 않았다.
- 각 실행 종료 시 해당 합성 계정의 대화·메시지·profile·Auth 계정만 제거했다. API·frontend 테스트 서버도 종료했다.

## 실행 결과 파일

모든 경로는 `data/chat/evaluation/runs/ragas/` 기준이다.

| 파일 | 범위 |
|---|---|
| `2026-10-06_local-e2e-before-migration-v1.json` | 복구 전 실제 HTTP·DB smoke 9개, 환경 오류 진단 |
| `2026-10-06_local-e2e-after-migration-v1.json` | migration 적용 후 동일 smoke 9개, 기본 답변 제한 15초 |
| `2026-10-06_service-ragas-baseline-v1.json` | 위 실제 검색·생성 입력으로 초기 RAG 3개, 네 지표 |
| `2026-10-06_balk-extended-timeout-e2e-v1.json` | 보크 1개, 별도 서버의 60초 답변 제한 진단 |
| `2026-10-06_balk-extended-timeout-diagnostic-v1.json` | 그 보크 진단 답변의 네 지표; 기본 baseline과 별도 집계 |
| `2026-10-06_local-ui-e2e-v1.json` | 실제 Next.js 화면 smoke 9개와 저장 답변 9개 재열기 |

초기 3개는 [reference dataset](../../data/chat/evaluation/cases/ragas_service_references_v1.json)을 사용한다. 모델 답변과 검색 chunk의 `needs_review` 상태를 정답 승인 근거로 사용하지 않았다.

## 검수된 기대 사실

- **사직 예매:** KBO 공식 [티켓 안내](https://www.koreabaseball.com/kbo/league/map.aspx)의 구단 자체 예매·롯데 `ticket.giantsclub.com` 링크를 확인했다. 실시간 좌석·가격·환불 조건은 reference에 넣지 않았다.
- **고척 음식물:** 서울시설공단 공식 [FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp)의 프로야구 음식물 반입 가능, 행사 성격별 제한, 재입장 시 음식물 반입 불가를 검수했다. 주류 허용에 관한 FAQ와 키움 SAFE 안내 이미지의 충돌은 별도 기록하고 reference에서 제외했다. 공식 운영 자료의 최신성은 추가 확인 대상이다.
- **보크:** 로컬 보존된 2026 공식야구규칙 원문 추출의 6.02(a), PDF 119–122쪽(인쇄 95–98쪽)을 확인했다. 주자 존재, 투수 위반, 한 베이스 안전진루, 플레이 계속 예외를 reference로 작성했다. 원문 추출 hash를 남겼다. 공식 온라인 간행물 목록에서 최신 PDF 본문을 다시 내려받아 대조한 결과는 아니다.

## 기본 설정 baseline

| 사례 | Faithfulness | Answer Relevancy | Context Precision | Context Recall | 수동 내용 점검 |
|---|---:|---:|---:|---:|---|
| 사직 예매 | 1.000 | 0.338 | 1.000 | 1.000 | 공식 예매처·기준일·검수 안내 확인 |
| 고척 음식물 | 제외 | 0.000 | 제외 | 제외 | 검색 0건; 실제 음식물 규정을 답하지 못함 |
| 보크 | 제외 | 제외 | 0.8875 | 1.000 | 15초 답변 시간 초과; 출처 개수만 말하는 대체 답변 |

원래 Tool 반환 순서로 검색 지표를 계산했고 Faithfulness는 생성기에 실제 전달된 상위 3개·본문 최대 6,000자 근거를 사용했다. 서버가 붙인 출처 안내 전의 모델 답변은 수집 지점에서 보존했다. 최종 답변 문자열에서 안내를 추정해 잘라내지 않았다.

고척은 router가 `stadium_food_guide`를 선택했으나 로컬 DB에는 해당 문서가 없었다. 기존 `stadium_bag_policy` 초안도 음료 제한 중심으로, 검수 reference의 음식물·재입장 사실이 없다. 빈 근거에서 허용 여부를 지어내지 않는 정책은 지켰지만 질문 해결에는 실패했다. 이 실패를 점수 평균으로 상쇄하지 않았다.

보크는 검색 Recall 1.0에도 답변 생성이 완료되지 않아 답변 지표를 `non_llm_response`로 제외했다. 고척의 Faithfulness는 `empty_generation_evidence`, Precision·Recall은 `empty_retrieval`로 제외했다. 제외를 0점·1점으로 대체하지 않았다. 기본 baseline에는 scored 7개, excluded 5개, judge error 0개가 있다. Tool별 표본은 1개이며 합격선을 정하지 않았다. 한국어의 수동 관련성 판단과 낮은 cosine 점수는 구분한다. 기본 영어 judge prompt의 언어 영향은 원인으로 확정하지 않았다.

보크 60초 진단에서는 설명 답변이 생성됐으며 Faithfulness 1.0, Answer Relevancy 0.208, Precision 0.8875, Recall 1.0을 얻었다. 기본 15초의 별도 UI 실행에서도 보크 설명이 생성됐다. 따라서 지연 변동과 timeout 위험이 확인된 것이며, 60초 설정만이 성공 원인이라는 결론은 아니다. 기본 설정을 변경하지 않았다. 진단 답변의 초보자 정의·한 베이스 진루는 확인했으나 플레이 계속 예외 설명은 생략돼 있었다.

## 실제 E2E 확인

- migration 후 HTTP smoke 9개 모두 HTTP 200, `assistant.completed`·`done` 수신, completed DB 답변과 SSE 본문 일치.
- 세 RAG Tool의 실제 이름은 기대 Tool과 일치했다. 세 후속 질문은 앞선 실제 경기 조회가 만든 DB 문맥을 사용하고 Tool을 다시 호출하지 않았다. 날짜는 기존 9월 fixture의 고정 날짜를 주입하지 않고 실행 당일 10월 6일이다.
- 예매의 온라인 Faithfulness 1.0은 SSE `done` 관측 뒤에 기록됐다. 보크 60초 진단도 실제 후속 온라인 Faithfulness 1.0을 확인했다. 빈 근거·fallback·비RAG는 평가하지 않았다.
- 실제 화면 smoke 9개 모두 입력 재활성화, 작성 중 표시 제거, 완료 이벤트 수신, 질문 표시, browser page error 없음.
- 저장된 대화를 실제 sidebar에서 다시 열어 9개 completed 답변 전체가 DB 조회 본문과 정확히 일치하는 paragraph로 렌더링됨을 확인했다. 9개 화면 캡처를 직접 확인했으며 호출한 Tool card는 완료 상태였다.
- 마지막 후속 답변 화면에서는 입력창이 화면 하단의 답변 일부와 겹쳐 보이는 장면이 있었다. DOM·재열기 검증은 통과했지만 화면 위치 개선은 별도 UX 후보로 남긴다.
- 기본 컴퓨터 제어 도구는 sandbox 초기화 오류로 실행되지 않아 설치된 Playwright·Chromium으로 확인했다. Turbopack은 `Next.js package not found` panic으로 UI가 반복 리로드되어 Webpack 모드로 실행했다. 제품 코드·Next 설정 변경은 하지 않았다.

## 설정·비용·보관

RAGAS 0.4.3의 collections 네 클래스를 사용했다. judge는 `gpt-4o-mini-2024-07-18`, temperature 0, 최대 출력 1,024 tokens, Answer Relevancy strictness 3, 평가 embedding은 `text-embedding-3-small`이다. judge SDK·Instructor·runner 재시도는 0, 지표별 timeout은 45초다. 생성은 기존 `gpt-5-mini`, 구장·예매 low / 야구 지식 medium reasoning을 유지하고 임시 transport에서 출력 상한 8,192 tokens를 추가했다.

온라인 평가 표본율 100%와 임시 예산 ledger는 검증용 프로세스에만 설정했다. 일반 서비스의 5% 설정이나 `.env`는 변경하지 않았다. 각 HTTP/UI 실행의 사전 예약 추정 상한은 $0.50, 각 별도 지표 실행은 $0.25다. 자동으로 전체 평가셋을 반복하지 않았다.

전체 6개 실행에서 실제 유료 HTTP 요청 96회를 관측했다. 반환된 usage에 미캐시 표준 단가를 적용한 추정 합계는 **약 $0.14947**이다. 취소 요청 2개는 usage를 받지 못해 전체 실제 청구액은 알 수 없다. 0원 처리하지 않았으며 billing 값은 null·사유로 남겼다. 청구서 확정액이 아니다. 단가는 공식 [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini), [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini), [embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small) 자료와 대조했다.

run에는 코드 revision, dataset·adapter·lockfile·service prompt·judge 구현/prompt source hash, 실제 tool args/filter, 근거 제한, case별 점수·제외·오류, usage·시간·수동 검토를 남겼다. 전체 graph stage trace 시간은 이번 harness에서 보존하지 못해 null·사유를 기록했다. provider 요청 시간, HTTP/SSE 시간, UI 완료 시간은 서로 다른 범위이며 합산하지 않는다. 독립 검수된 기대 chunk ID가 없어 hit@1/hit@3은 제외했다.

합성 답변 전문·평가 입력·화면 캡처·임시 실행 harness는 `/private/tmp/baseball-ragas-*`에만 보관했다. Git 결과에 계정·conversation/message ID, cookie·token·API key·실제 사용자 대화는 남기지 않았다. 전문을 영구 보관하지 않으므로 동일 답변의 영구 재평가는 할 수 없고, 비교 시 같은 case를 다시 생성해야 한다.

## 다음 품질 개선 후보

1. 공식 음식물·재입장 안내를 source pipeline의 검수 절차로 보강하고 동일 질문 재측정.
2. 보크의 답변 생성 latency 분포와 근거 길이를 측정해 기본 timeout·generation policy를 결정.
3. reference의 사람 검수, 기대 chunk ID 검수, 추가 규칙 조건·부분 근거·정책 case를 보강한 확대 baseline.

이번 작업은 측정과 초기 기준선 구축이며, 위 후속 품질 개선까지 완료한 상태가 아니다.

## 최종 검증

기존 chat 데이터 validator 통과: cases 30, candidates 5, manual runs 2.
추가 run 6개와 reference 3개는 실제 adapter 입력 검증, 점수/제외 null 규칙,
예산·usage 개수, hash·설정 일치, 민감 필드 미포함, HTTP·DB·UI 결과 assertion을 통과했다.
마지막 DB 확인에서 합성 Auth 계정 0개, 기존 profile 1개, RAG chunk 72개를 확인했다.
`git diff --check`도 통과했다. 이번 측정 결과와 문서는 아직 커밋하지 않았다.
