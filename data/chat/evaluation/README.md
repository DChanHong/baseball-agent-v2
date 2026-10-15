# Chat Evaluation

## 목적

Manual QA 실행 결과를 보관하고, 실패 또는 애매한 사례를 사람이 검토한 뒤 회귀 평가에 사용할 정식 case로 승격한다.

```text
Manual QA Run
→ Candidate
→ Human Review
→ Evaluation Case
→ Regression Evaluation
```

## 디렉터리 역할

```text
candidates/  실패·애매 사례의 검토 대기열
cases/       기대 동작이 확정된 재사용 평가셋
runs/manual/ 브라우저 기반 수동 QA 실행 결과
runs/answer-model/ 고정 공개 근거를 사용하는 답변 모델 비교 milestone
runs/ragas/ RAGAS 지표 실행 요약 (합성 지표 smoke와 서비스 baseline은 scope로 구분)
schemas/     각 데이터 파일의 JSON Schema
```

## 파일 규칙

- JSONL은 UTF-8 한 줄당 객체 하나를 사용한다.
- JSON run 파일은 한 번의 실행과 전체 집계를 함께 기록한다.
- `cases/`와 검토 이력이 있는 `candidates/`는 Git에 보관한다.
- `runs/`에는 비교 기준이 되는 baseline 또는 milestone 실행만 보관한다.
- candidate가 없을 때 빈 JSONL을 만들지 않는다. 첫 candidate가 발생하면 `manual_chat_qa_candidates.jsonl`을 생성한다.
- ID는 파일 안에서 유일해야 하며 한 번 사용한 ID의 의미를 바꾸지 않는다.

## 결과 분류

```text
passed     기대 Tool, 결과, 답변, UI 상태가 허용 범위에 있음
ambiguous  답변은 가능하지만 근거·표현·Tool 선택·UI 상태가 불안정함
failed     명확한 기대 동작과 다르거나 요청을 완료하지 못함
not_run    아직 실행하지 않았거나 준비 조건을 충족하지 못함
```

## 실패 유형

```text
tool_routing
tool_input
structured_data_freshness
rag_retrieval
rag_grounding
answer_quality
answer_policy
source_limitation
ui_sse
security_policy
runtime_error
```

## 개인정보와 민감정보

다음을 저장하지 않는다.

```text
실제 사용자 대화 전문
user_profile_id
운영 conversation_id와 message_id
이메일 등 개인정보
Authorization header
cookie와 token
API key와 환경변수 값
```

초기 QA는 합성 질문만 사용한다. 실제 사용에서 발견한 문제를 옮길 때는 의미를 유지한 `sanitized_input`으로 재작성한다. Assistant 응답 전문은 기본적으로 저장하지 않고 `observed_behavior`로 요약한다.

답변 모델 비교의 `cases/answer_model_comparison_cases.json`은 공개 RAG 결과를
고정한 별도 fixture다. 기존 chat case schema 및 chat validator 대상과 구분한다.
`backend/scripts/compare_answer_models.py`가 입력을 기존 답변 request 계약으로
구성하고, 생성 답변은 실제 서비스의 schema·ref·limitation 검증을 거친다.
`runs/answer-model/`에는 시간·계약 검증 결과·검토 주체가 명시된 품질 점검 요약을 보관한다.
검토용 합성 답변 전문은 `/private/tmp`에만 만들고 Git에 넣지 않는다.

`runs/ragas/2026-10-05_synthetic-metric-demo-v1.json`은 가상 구장 입력의
실제 judge·embedding API smoke 결과다. `service_baseline=false`이며
실서비스 검색/답변·공식 정책 정답셋 평가 결과로 해석하지 않는다.
기존 manual run schema/validator 대상과 구분한다.
설정·hash·점수·오류·시간·token usage만 저장하고 입력/답변 전문은 임시 파일에 둔다.
실행과 해석은 `docs/work/2026-10-05-ragas-synthetic-metric-demo.md`를 따른다.

## 검증

저장된 JSON과 JSONL은 `schemas/`의 대응 Schema로 검증한다. 정식 case는 `review_status=approved`인 항목만 회귀 평가 입력으로 사용한다.

저장소 루트에서 다음 명령을 실행한다.

```bash
backend/.venv/bin/python backend/scripts/validate_chat_evaluation_data.py
```

2026-10-06 첫 서비스 baseline과 실제 API·DB·화면 E2E 결과는
[실행 기록](../../../docs/work/2026-10-06-ragas-service-baseline-e2e.md)을 따른다.
`cases/ragas_service_references_v1.json`은 공식 원문을 agent가 검수한 별도
reference dataset이며 `human_reviewed=false`를 유지한다. 10월 6일 run은
기본 15초 baseline과 60초 진단을 분리하며, 실패·제외도 측정 결과에 포함한다.


## 50개 Agent 평가 후보 — 2026-10-14

[후보 데이터셋](cases/agent_golden_candidates_v1.json)은 10월 6일 계획에 따라 작성한
50개의 합성 질문이다. **구성 작업만 수행했으며 실제 API 실행·RAGAS 평가는 아직 하지 않았다.**
기존 manual case 30개와 초기 reference 3개는 수정하지 않았다.

| 영역 | 개발용 초안 | 최종 확인용 초안 | 합계 |
|---|---:|---:|---:|
| 구장 안내 | 10 | 5 | 15 |
| 예매 | 7 | 3 | 10 |
| 야구 지식 | 11 | 4 | 15 |
| 복합·후속 | 4 | 1 | 5 |
| 근거 부족·범위 밖 | 3 | 2 | 5 |
| 합계 | 35 | 15 | 50 |

### 검수 상태와 사용 제한

- `candidate_draft`, `frozen=false`, 전 사례 `human_reviewed=false`다. 사람이 검수한 골든셋으로 표현하지 않는다.
- 질문, 고정 문맥, 기대 Tool·filter, reference 후보, 필수 사실, 금지 주장, 출처 locator와 검수 상태를 기록했다.
- 최초 작성 때 KT 주차·대전 수유실은 보류했으나 review1에서 공식 브라우저 화면을 확인해 보류를 해제했다. 현재 `needs_source_review`, `reference_answer=null`인 정책 사례는 삼성 우천취소 환불(`golden_ticket_009`) 1개다.
- 사직 교통·구장샵은 review1에서 현재 공식 브라우저 화면을 다시 확인했다. 저장된 source content hash는 보존된 7월 29일 HTML의 것으로, 현재 웹 원문 bytes hash와 구별한다.
- 야구 규칙은 공식 CDN의 2026 PDF를 새로 읽었다. 전체 파일과 사용한 페이지 추출 hash를 기록했으며 PDF·페이지 전문은 임시 경로에만 보관했다.
- 웹 도구로 확인한 현재 정책 페이지는 URL·locator·확인일을 기록했으나 원본 bytes hash는 확보하지 못했다. 없는 hash를 만들지 않고 null·사유로 표시했다. 평가 전 공개 원문 snapshot을 확보한다.
- `local_corpus_snapshot`은 저장소 파일 hash이며 DB corpus snapshot이 아니다. DB에 접속하지 않았다.
- `local_candidate_chunks`는 local-labels1에서 같은 구장의 모든 로컬 문서 유형으로 확장해 사실 span과 0/1/2 등급을 agent가 검수했다. logical document/revision ID는 여전히 null이고 DB 활성 문서는 미확인이다. `expected_topic_ids`는 검수 완료 chunk ID가 아니다.
- `local_coverage`의 full/partial/missing은 검수한 유한 로컬 pool에서 필수 검색 사실을 포함하는지 나타낸다. 운영 DB coverage나 실제 retrieval 성능을 확정하는 결과가 아니다.
- 동일 사실 그룹은 분할을 넘지 않도록 묶었지만 분할은 아직 제안이다. 검수 후 corpus와 함께 고정한다. 최종 확인용 사례는 튜닝 과정의 반복 실행에서 제외한다.

### 평가 성공 판정

`allowed_behaviors`의 근거 부족 안내는 안전한 fallback으로 허용한다는 뜻이며,
답변 가능한 질문을 해결했다는 뜻은 아니다. `source_answerable` 사례는 필수 사실 충족과
금지 주장 미포함을 별도로 검사한다. 완료 이벤트·저장 성공, 안전한 fallback, 질문 해결을
독립적으로 기록한다. 출처 기반 사실 정답이 없는 정책 사례 5개는 우선 agent 동작만 평가한다.

복합·후속 질문은 실제 생성된 이전 답변을 저장한 것이 아니라 고정 합성 fixture를 사용한다.
현재 API runner와 RAGAS adapter가 이 fixture를 자동으로 지원한다고 가정하지 않는다.
특히 `golden_mixed_003`의 경기는 실제 KBO 일정이 아닌 가상 상태 처리 검사다.
`golden_mixed_005`의 두 구단 비교는 single-tool 구조의 한계를 드러내는 사례이며,
추가 질문·명시적 부분 답변을 허용해도 전체 질문 해결 여부는 별도로 판정한다.

### 검증

별도 [JSON Schema](schemas/agent_golden_candidate.schema.json)와 아래 validator를 사용한다.
기존 manual validator에 억지로 합치지 않는다. 이 validator는 draft 전용이며,
사람 검수·승격 시 별도의 고정 골든셋 계약이 필요하다.

```bash
backend/.venv/bin/python backend/scripts/validate_agent_golden_dataset.py
```

검사는 50개 분포, 분야별 35/15 분할, ID·질문 중복, 사실 그룹의 분할 누출,
기존 case ID 연결, 필수 사실의 출처 연결, 미검수 정답 null, PDF 페이지 hash 존재,
로컬 문서/chunk ID, dataset·로컬 파일 hash를 확인한다. 네트워크·DB·유료 모델 호출은 없다.
수정 후 `content_sha256`은 해당 필드만 제외한 JSON을 `ensure_ascii=False`,
`sort_keys=True`, `separators=(",", ":")`로 UTF-8 직렬화한 SHA-256이다.
Schema를 다시 내보내려면 validator의 `--write-schema` 옵션을 사용한다.

### 질문 목록

아래 목록은 검토 편의를 위한 색인이다. 기대답변·필수 사실·금지 주장·출처는 JSON을 본다.

| ID | 영역 | 분할 초안 | 질문 |
|---|---|---|---|
| `golden_guide_001` | 구장 안내 | 개발용 | 고척돔 음식물 반입 가능해? |
| `golden_guide_002` | 구장 안내 | 개발용 | 고척 야구 보러 가는데 내부 주차장에 차 대면 돼? |
| `golden_guide_003` | 구장 안내 | 개발용 | 사직구장 지하철 몇 호선 타고 어느 역에서 내려? |
| `golden_guide_004` | 구장 안내 | 개발용 | 잠실 야구 보러 가면 주차비가 항상 5분당 요금이야? |
| `golden_guide_005` | 구장 안내 | 개발용 | 수원 KT위즈파크는 경기일 주차 예약 없이 가도 돼? |
| `golden_guide_006` | 구장 안내 | 개발용 | 문학구장 승용차 주차 요금이 얼마고 경기 취소되면 돌려줘? |
| `golden_guide_007` | 구장 안내 | 개발용 | 창원NC파크에 레이저 포인터 가져가도 돼? |
| `golden_guide_008` | 구장 안내 | 개발용 | 광주 챔필에 유리병 음료 들고 들어갈 수 있어? |
| `golden_guide_009` | 구장 안내 | 개발용 | 라팍에 뜨거운 국물 음식도 가져가도 되는 거야? |
| `golden_guide_010` | 구장 안내 | 개발용 | 대전 볼파크에 접이식 의자 가져가도 돼? 잔디석도 같아? |
| `golden_guide_011` | 구장 안내 | 최종 확인용 | 고척돔 안에서 담배 피울 수 있어? |
| `golden_guide_012` | 구장 안내 | 최종 확인용 | 고척에서 야구 보다가 지갑 잃어버렸어. 어디에 문의해? |
| `golden_guide_013` | 구장 안내 | 최종 확인용 | 대전 새 볼파크에 아기랑 가는데 수유실 있어? |
| `golden_guide_014` | 구장 안내 | 최종 확인용 | 사직에서 유니폼 사려면 구장 어디로 가야 해? |
| `golden_guide_015` | 구장 안내 | 최종 확인용 | 잠실 LG 홈경기에 30개월 아기 데려가면 자리도 무료야? |
| `golden_ticket_001` | 예매 | 개발용 | 사직 예매 어디서 해? |
| `golden_ticket_002` | 예매 | 개발용 | 우리 팀 경기 예매 방법 알려줘 |
| `golden_ticket_003` | 예매 | 개발용 | SSG 문학 홈경기 표 어디서 사? |
| `golden_ticket_004` | 예매 | 개발용 | KIA 광주 홈경기 예매 사이트 알려줘 |
| `golden_ticket_005` | 예매 | 개발용 | 한화 대전 홈경기는 어디서 예매해? |
| `golden_ticket_006` | 예매 | 개발용 | LG 잠실 홈경기 일반 예매는 며칠 전 몇 시에 열려? |
| `golden_ticket_007` | 예매 | 개발용 | 키움 홈경기 표 4장 중 1장만 취소할 수 있어? |
| `golden_ticket_008` | 예매 | 최종 확인용 | 두산 잠실 홈경기는 LG랑 같은 예매 사이트야? |
| `golden_ticket_009` | 예매 | 최종 확인용 | 삼성 홈경기 우천취소면 발권한 표도 자동 환불돼? |
| `golden_ticket_010` | 예매 | 최종 확인용 | KT 수원 홈경기 표는 티켓링크에서 예매하는 게 맞아? |
| `golden_knowledge_001` | 야구 지식 | 개발용 | 보크가 뭐야? |
| `golden_knowledge_002` | 야구 지식 | 개발용 | 인필드 플라이는 어떤 조건에서 선언되고 공을 놓치면 어떻게 돼? |
| `golden_knowledge_003` | 야구 지식 | 개발용 | 포스아웃이랑 태그아웃 차이가 뭐야? |
| `golden_knowledge_004` | 야구 지식 | 개발용 | 낫아웃이면 1루에 주자가 있어도 무조건 뛸 수 있어? |
| `golden_knowledge_005` | 야구 지식 | 개발용 | 1루 지나 외야 페어 지역에 떨어진 공이 파울로 굴러가면 파울이야? |
| `golden_knowledge_006` | 야구 지식 | 개발용 | 3루 주자가 먼저 홈 밟았는데 마지막 아웃이 포스아웃이면 점수야? |
| `golden_knowledge_007` | 야구 지식 | 개발용 | 투스트라이크에서 번트가 파울이면 계속 치는 거야? |
| `golden_knowledge_008` | 야구 지식 | 개발용 | 볼 데드 때는 주자가 마음대로 한 베이스씩 가도 돼? |
| `golden_knowledge_009` | 야구 지식 | 개발용 | 몸에 맞으면 공이 스트라이크 존 안이어도 무조건 1루야? |
| `golden_knowledge_010` | 야구 지식 | 개발용 | 2026 KBO 피치클락 투수랑 타자 위반하면 각각 어떻게 돼? |
| `golden_knowledge_011` | 야구 지식 | 개발용 | ABS가 체크스윙까지 자동으로 판정하는 거야? |
| `golden_knowledge_012` | 야구 지식 | 최종 확인용 | 폭투랑 포일은 어떻게 달라? |
| `golden_knowledge_013` | 야구 지식 | 최종 확인용 | 희생플라이는 잡혀야만 기록돼? 놓쳐도 점수 나면 가능한가? |
| `golden_knowledge_014` | 야구 지식 | 최종 확인용 | 주자 2루만 있을 때 볼넷이면 그 주자도 3루로 가? |
| `golden_knowledge_015` | 야구 지식 | 최종 확인용 | 2026 KBO 체크스윙 판독은 일반 판독 기회를 써? 번트도 신청돼? |
| `golden_mixed_001` | 복합·후속 | 개발용 | 사직 처음 가는데 지하철이랑 가져가면 안 되는 가방 알려줘 |
| `golden_mixed_002` | 복합·후속 | 개발용 | 그럼 거기 경기 표는 어디서 사? |
| `golden_mixed_003` | 복합·후속 | 개발용 | 그 경기 몇 시에 시작해? |
| `golden_mixed_004` | 복합·후속 | 개발용 | 아니 이번엔 고척이야. 내부 주차는 가능해? |
| `golden_mixed_005` | 복합·후속 | 최종 확인용 | 두산 잠실이랑 KT 수원 홈경기 예매처가 같은지 비교해줘 |
| `golden_scope_001` | 근거 부족·범위 밖 | 개발용 | 오늘 고척 1루 쪽 표 몇 장 남았어? |
| `golden_scope_002` | 근거 부족·범위 밖 | 개발용 | 우리 팀 홈경기 취소 수수료 얼마야? |
| `golden_scope_003` | 근거 부족·범위 밖 | 개발용 | 사직에 유모차 맡기는 곳 위치 정확히 알려줘 |
| `golden_scope_004` | 근거 부족·범위 밖 | 최종 확인용 | 고척돔 콘서트도 야구 때처럼 음식물 들고 들어가면 돼? |
| `golden_scope_005` | 근거 부족·범위 밖 | 최종 확인용 | 야구 말고 내일 살 주식 하나 추천해줘 |

### 다음 순서

1. 삼성 우천취소 환불 원문의 적용 범위 충돌을 해소한다.
2. reference·필수 사실·금지 주장과 retrieval relevance label을 검수한다.
3. 사람 검수 상태, 분할 및 실제 corpus snapshot을 고정한다.
4. follow-up·다중 Tool 수집 계약과 재실행 runner를 준비한다.
5. 예산·중단 정책을 확정한 뒤 현재 agent의 기준선을 측정한다.


## 출처·기대답변 대조 — 2026-10-14 review1

50개 후보를 공식 원문·프로젝트 계약·합성 문맥과 대조했다. KT 주차와 대전 수유실 보류를 해제하고 사직 현재 페이지도 확인했다. 삼성 환불 1개는 원문 내 적용 범위 충돌로 보류한다. 사람이 승인한 골든셋은 아니며 API/RAGAS 실행은 하지 않았다.

G=구장 / T=예매 / K=야구 지식 / M=복합·후속 / S=근거 부족·범위 밖이다. 번호는 JSON case ID 마지막 세 자리와 대응한다. 예매 시간·정책은 일반 홈경기 기준이며 특별경기 공지는 별도다.

| 질문 | 기대답변 | 출처 | 확인할 점 |
|---|---|---|---|
| G01 고척돔 음식물 반입 가능해? | 프로야구 때 음식물을 가져갈 수 있지만 행사별 제한이 있으며 재입장 때는 음식물 반입이 불가하다. | [고척 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 프로야구·공연 구분. 재입장·주류는 별도. |
| G02 고척 야구 보러 가는데 내부 주차장에 차 대면 돼? | 프로야구 때 고척 내부 주차장은 이용 불가하며 대중교통 또는 인근 민영주차장을 확인한다. | [키움 예매 안내](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 경기일 내부 주차 불가와 평시 요금을 혼동하지 않음. |
| G03 사직구장 지하철 몇 호선 타고 어느 역에서 내려? | 롯데 공식 안내는 부산 도시철도 3호선 사직역 또는 종합운동장역을 안내한다. | [롯데 구장 안내](https://www.giantsclub.com/html/?pcode=207) | 부산 3호선. 실시간 운행·도보시간 보장 제외. |
| G04 잠실 야구 보러 가면 주차비가 항상 5분당 요금이야? | 평시 후불요금과 프로야구 선불제를 구분한다. 선불요금은 소형 6,000원·대형 12,000원이며 만차 시 입차가 제한될 수 있다. | [서울시 주차 안내](https://stadium.seoul.go.kr/about/park-info) | 평시 후불/경기일 선불·만차 제한 구분. |
| G05 수원 KT위즈파크는 경기일 주차 예약 없이 가도 돼? | 프로야구 경기일에는 일반 차량의 사전 주차예약이 필요하며 미예약 차량은 주차할 수 없다. 경기 시작 2시간 전부터 통제한다. 25인승 소형버스 이상과 장애인 차량은 예약 제외 대상으로 입차 시 요금을 납부한다. | [KT 주차 안내](https://www.ktwiz.co.kr/wizpark/parking) | 일반차량 원칙과 장애인·25인승 이상 예외 구분. |
| G06 문학구장 승용차 주차 요금이 얼마고 경기 취소되면 돌려줘? | 승용차 전일 주차권은 2,000원이며 행사 취소 사유로 주차요금이 환불되지는 않는다. | [SSG 주차 안내](https://www.ssglanders.com/stadium/parking) | 티켓 환불과 주차요금 환불을 구분. |
| G07 창원NC파크에 레이저 포인터 가져가도 돼? | KBO 공통 안전정책은 레이저 포인터 반입을 제한한다. 방문 전 구단 안내도 확인한다. | [KBO SAFE](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | KBO 공통 금지 원칙. 구단 특별 허용을 지어내지 않음. |
| G08 광주 챔필에 유리병 음료 들고 들어갈 수 있어? | KBO 공통 안전정책은 유리병 반입을 제한하며 구단 세부 안내도 확인한다. | [KBO SAFE](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | PET·캔 허용과 유리병 제한을 혼동하지 않음. |
| G09 라팍에 뜨거운 국물 음식도 가져가도 되는 거야? | 금지품목이 아닌 음식은 허용 범위 내 반입할 수 있으나 뜨거운 국물 등 안전·관람환경을 해치는 음식은 제한될 수 있다. | [KBO SAFE](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 뜨거운 국물은 제한 가능. 모든 음식 전면 금지는 아님. |
| G10 대전 볼파크에 접이식 의자 가져가도 돼? 잔디석도 같아? | 휴대용 의자는 원칙적으로 제한된다. 구단이 특별히 허용한 잔디석 등의 예외가 있을 수 있어 대전의 적용 여부는 확인해야 한다. | [KBO SAFE](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 대전 잔디석의 실제 예외 허용은 미확인. |
| G11 고척돔 안에서 담배 피울 수 있어? | 경기장 내부는 금연이며 공식 안내의 외부 흡연 부스를 이용한다. | [고척 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 외부 지정 장소 안내. 부스 수·위치 추가 단정 제외. |
| G12 고척에서 야구 보다가 지갑 잃어버렸어. 어디에 문의해? | 프로야구 경기 때 분실물은 홈구단 키움이 수거·관리하므로 키움에 문의한다. | [고척 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 프로야구 때만 키움 관리. 실제 보관 여부는 조회 불가. |
| G13 대전 새 볼파크에 아기랑 가는데 수유실 있어? | 한화 공식 대전 볼파크 안내의 편의시설 탭에서 1층 내부 수유실을 확인할 수 있다. 세부 위치와 이용시간은 현장 안내를 확인한다. | [한화 볼파크](https://www.hanwhaeagles.co.kr/MN/EP/MNEPPI01.do) | 1층 내부 목록 확인. 게이트·운영시간은 미확인. |
| G14 사직에서 유니폼 사려면 구장 어디로 가야 해? | 롯데 공식 구장샵 안내는 유니폼샵을 사직 광장 1루측 컨테이너 1층, 프로페셔널샵을 구장 1층 중앙출입구 오른편으로 안내한다. | [롯데 구장샵](https://www.giantsclub.com/html/?pcode=367) | 유니폼샵·프로페셔널샵 구분. 재고·영업 보장 제외. |
| G15 잠실 LG 홈경기에 30개월 아기 데려가면 자리도 무료야? | 36개월 미만은 무료입장이 가능하지만 별도 좌석이 제공되지 않는다. 좌석을 점유하려면 티켓을 구매해야 한다. | [LG 티켓 안내](https://www.lgtwins.com/ticket/general) | LG 홈경기 조건. 무료입장과 좌석 점유를 구분. |
| T01 사직 예매 어디서 해? | 롯데 자체 예매(ticket.giantsclub.com)에서 해당 구단 홈경기를 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | 롯데 홈경기. 잔여석·오픈시간은 별도. |
| T02 우리 팀 경기 예매 방법 알려줘 | NC 자체 예매(ticket.ncdinos.com)에서 해당 구단 홈경기를 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) + 고정 합성 문맥 | favorite_team_id=NC fixture가 있어야 NC로 해석. |
| T03 SSG 문학 홈경기 표 어디서 사? | SSG 자체 예매(ticket.ssg.com)에서 해당 구단 홈경기를 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | SSG 자체 예매. 다른 구단 플랫폼 혼합 금지. |
| T04 KIA 광주 홈경기 예매 사이트 알려줘 | 티켓링크(www.ticketlink.co.kr)에서 해당 구단 홈경기를 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | KIA 홈경기 기준. 실시간 판매 가능 여부와 구분. |
| T05 한화 대전 홈경기는 어디서 예매해? | 티켓링크(www.ticketlink.co.kr)에서 해당 구단 홈경기를 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | 한화 홈경기 기준. 오픈 시각·수수료 추가 생성 제외. |
| T06 LG 잠실 홈경기 일반 예매는 며칠 전 몇 시에 열려? | 일반 홈경기는 관람 7일 전 오전 11시부터 경기 시작 후 1시간까지 예매 가능하다. | [LG 티켓 안내](https://www.lgtwins.com/ticket/general) | 일반 홈경기 기준. 포스트시즌·특별경기 공지 별도. |
| T07 키움 홈경기 표 4장 중 1장만 취소할 수 있어? | 부분취소는 불가하며 전체 취소 후 재예매해야 한다. 기존 좌석 확보는 보장되지 않고 취소 기한·수수료도 확인해야 한다. | [키움 예매 안내](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 전체 취소 후 기존 좌석 재확보를 보장하지 않음. |
| T08 두산 잠실 홈경기는 LG랑 같은 예매 사이트야? | NOL 티켓(nol.yanolja.com)에서 해당 구단 홈경기를 확인한다. LG 홈경기는 티켓링크이므로 홈팀을 구분한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | 같은 잠실이어도 두산과 LG 홈경기 구분. |
| T09 삼성 홈경기 우천취소면 발권한 표도 자동 환불돼? | 정답 보류. 구매수단·발권 상태를 확인하고 공식 안내의 충돌을 설명한다. | [삼성 환불 안내](https://www.samsunglions.com/m/ticket/score_4_1_4.asp) | 보류: 원문 내 환불 항목 충돌. 구매수단·발권상태별 최신 확인 필요. |
| T10 KT 수원 홈경기 표는 티켓링크에서 예매하는 게 맞아? | KBO 공식 예매처 안내에서 KT는 티켓링크에 속한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | KT 홈경기 기준. 앱 정책·수수료는 별도 검수. |
| K01 보크가 뭐야? | 보크는 주자가 있을 때 투수의 규칙 위반에 대해 선고하며 원칙적으로 각 주자에게 한 베이스 안전진루권을 준다. 다만 타자가 안타·실책·4사구 등으로 1루에 도달하고 다른 모든 주자도 최소 한 베이스 진루하면 플레이가 계속된다. | [2026 규칙 6.02(a) 본문·벌칙](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 주자 존재·진루 결과·플레이 계속 예외 필요. |
| K02 인필드 플라이는 어떤 조건에서 선언되고 공을 놓치면 어떻게 돼? | 무사·1사에 1·2루 또는 만루, 쉽게 잡을 페어 뜬공이 대상이다. 번트·직선타는 제외되며 선고 시 타자 아웃, 볼은 인플레이다. | [2026 규칙 용어 40; 5.09(a)(5)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 무사/1사·1/2루 또는 만루·번트/직선타 제외. |
| K03 포스아웃이랑 태그아웃 차이가 뭐야? | 타자 출루로 밀려나는 주자는 포스 상태라 공을 가진 야수가 다음 베이스에 닿아 아웃시킬 수 있다. 포스가 풀리면 주자 신체 태그가 필요하다. | [2026 규칙 용어 30·75; 5.09(b)(6)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 포스 상태 해제 구분. 어필 아웃은 별도 규칙. |
| K04 낫아웃이면 1루에 주자가 있어도 무조건 뛸 수 있어? | 제3스트라이크 미포구 때 1루가 비었거나 2아웃이면 타자는 주자가 될 수 있다. 무사·1사에 1루주자가 있으면 타자 아웃이다. | [2026 규칙 5.05(a)(2); 5.09(a)(3)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 1루주자·아웃카운트 조건 누락 금지. |
| K05 1루 지나 외야 페어 지역에 떨어진 공이 파울로 굴러가면 파울이야? | 야수에게 먼저 닿지 않은 타구가 1루를 지난 외야 페어 지역에 처음 떨어졌다면, 이후 파울 지역으로 굴러가도 페어다. | [2026 규칙 용어 25 FAIR BALL](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 야수 접촉 전 외야 최초 낙하를 전제. |
| K06 3루 주자가 먼저 홈 밟았는데 마지막 아웃이 포스아웃이면 점수야? | 제3아웃이 포스아웃이면 먼저 홈을 밟았더라도 득점이 인정되지 않는다. | [2026 규칙 5.08(a) 부기 (2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 제3아웃인 포스아웃과 다른 아웃 구분. |
| K07 투스트라이크에서 번트가 파울이면 계속 치는 거야? | 포구되지 않은 번트 파울은 제3스트라이크로 아웃이다. 번트 파울 플라이가 포구되면 플라이 아웃이다. | [2026 규칙 5.09(a)(4); 9.15(a)(4) 예외; 용어72](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 미포구 번트 파울 삼진 / 포구 파울 플라이 아웃 구분. |
| K08 볼 데드 때는 주자가 마음대로 한 베이스씩 가도 돼? | 볼 데드는 플레이가 일시정지된 상태로 임의 진루는 할 수 없다. 해당 규칙에 따라 안전진루권이 주어지거나 원래 베이스로 돌아가야 한다. | [2026 규칙 용어20; 5.06(c)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 볼 데드가 항상 한 베이스 진루는 아님. |
| K09 몸에 맞으면 공이 스트라이크 존 안이어도 무조건 1루야? | 바운드하지 않은 투구가 스트라이크 존에서 타자에게 닿으면 스트라이크다. 몸에 맞았다는 이유만으로 1루가 주어지지 않는다. | [2026 규칙 5.05(b)(2)(A)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 바운드하지 않은 투구 전제. 피하려 했는지와 구분. |
| K10 2026 KBO 피치클락 투수랑 타자 위반하면 각각 어떻게 돼? | 2026 KBO리그에서 투·포수 위반에는 볼, 타자 위반에는 스트라이크가 부과된다. | [KBO 2026 규정](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 2026 KBO리그 기준. MLB·이전 시즌 경고 정책 혼합 금지. |
| K11 ABS가 체크스윙까지 자동으로 판정하는 거야? | ABS는 정규 투구의 위치를 추적해 볼·스트라이크 결과를 전달한다. 체크스윙 여부는 ABS 위치 판정과 구별한다. | [KBO 2026 규정](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 투구 위치와 스윙 여부를 구분. |
| K12 폭투랑 포일은 어떻게 달라? | 주자 진루를 초래한 투구에서 보통 수비로 처리 불가능하면 폭투, 처리 가능했는데 포수가 놓치면 포일로 기록한다. | [2026 규칙 9.13(a)(b)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 보통 수비 가능 여부와 실제 진루 기준. |
| K13 희생플라이는 잡혀야만 기록돼? 놓쳐도 점수 나면 가능한가? | 무사·1사 때 외야의 플라이·직선타로 득점하면 기록될 수 있다. 놓쳤더라도 잡았어도 득점 가능했다고 기록원이 판단하면 해당한다. | [2026 규칙 9.08(e)(1)(2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 무사/1사·득점·공식기록원 판단 조건 필요. |
| K14 주자 2루만 있을 때 볼넷이면 그 주자도 3루로 가? | 볼넷은 타자에게 1루를 주며 밀려나야 하는 주자만 강제 진루한다. 2루에만 있는 주자는 강제로 3루에 가지 않는다. | [2026 규칙 5.05(b)(1)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 2루에만 있는 주자 전제. 만루와 구분. |
| K15 2026 KBO 체크스윙 판독은 일반 판독 기회를 써? 번트도 신청돼? | 체크스윙은 일반 판독과 별도로 팀당 2회 기회가 주어지며 번트 시도는 대상이 아니다. 연장전에는 1회 추가되고 번복되면 기회를 유지한다. | [KBO 2026 규정](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 별도 판독 기회·연장 추가·번트 제외 조건. |
| M01 사직 처음 가는데 지하철이랑 가져가면 안 되는 가방 알려줘 | 부산 3호선 사직역·종합운동장역을 이용한다. KBO 공통 가방·쇼핑백 크기와 개수 제한을 확인한다. | [롯데 구장 안내](https://www.giantsclub.com/html/?pcode=207) + [KBO SAFE](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 교통과 가방 모두 답해야 해결 성공. |
| M02 그럼 거기 경기 표는 어디서 사? | 선택된 창원NC파크의 NC 홈경기는 NC 자체 예매처 ticket.ncdinos.com에서 확인한다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) + 고정 합성 문맥 | 창원·NC 고정 문맥 필요. 공식 페이지는 문맥 자체의 출처가 아님. |
| M03 그 경기 몇 시에 시작해? | 고정된 합성 경기 문맥의 시작 시각인 18시 30분을 안내한다. | 프로젝트 응답·routing 계약 + 고정 합성 문맥 | 실제 일정이 아닌 합성 selected_game.start_time 검사. |
| M04 아니 이번엔 고척이야. 내부 주차는 가능해? | 새로 명시한 고척을 기준으로, 프로야구 경기 때 내부 주차장 이용이 불가함을 안내한다. | [키움 예매 안내](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) + 고정 합성 문맥 | 이전 사직보다 새로 명시한 고척 우선. |
| M05 두산 잠실이랑 KT 수원 홈경기 예매처가 같은지 비교해줘 | 두산은 NOL 티켓, KT는 티켓링크로 예매처가 다르다. | [KBO 예매처](https://www.koreabaseball.com/kbo/league/map.aspx) | 두 구단 모두 설명해야 전체 해결. 현 single-tool 한계 별도 기록. |
| S01 오늘 고척 1루 쪽 표 몇 장 남았어? | 실시간 잔여석 조회를 지원하지 않으므로 수량을 확정할 수 없다고 안내한다. | 프로젝트 응답·routing 계약 | 재고 수량 생성 금지. 공식 예매처 연결은 허용. |
| S02 우리 팀 홈경기 취소 수수료 얼마야? | 어느 구단 홈경기인지 먼저 묻는다. | 프로젝트 응답·routing 계약 | 선호팀·선택구장 없는 fixture. 팀 추측 금지. |
| S03 사직에 유모차 맡기는 곳 위치 정확히 알려줘 | 확인된 근거가 없어 위치를 확정할 수 없다고 안내하고 공식 문의를 권한다. | [롯데 구장샵](https://www.giantsclub.com/html/?pcode=367) | corpus 부족 조건. 시설 자체가 없다고 단정 금지. |
| S04 고척돔 콘서트도 야구 때처럼 음식물 들고 들어가면 돼? | 행사별 제한이 달라 공연 주최 측 공지 확인이 필요하다고 안내한다. | [고척 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 공연명·주최 공지 없는 상태. 야구 정책 전용 금지. |
| S05 야구 말고 내일 살 주식 하나 추천해줘 | 야구·직관 서비스 범위 밖 요청임을 안내한다. | 프로젝트 응답·routing 계약 | 야구 서비스 범위 밖. 투자 답변·야구 Tool 호출 제외. |


## 로컬 검색 정답 연결 — 2026-10-14 local-labels1

50개를 사실 단위로 분류했다. API·DB·검색 embedding·RAGAS는 실행하지 않았다.

| 분류 | 사례 수 |
|---|---:|
| 로컬 필수 검색 사실 전체 포함 | 10 |
| 일부 포함 | 10 |
| 검수한 로컬 pool에서 필수 검색 사실 없음 | 8 |
| 원문 정책 보류 | 1 |
| 야구지식 서비스 chunk 파일 미확보 | 15 |
| 검색 정답 평가 비대상: 정책 5개·합성 직접응답 1개 | 6 |
| 합계 | 50 |

### label 해석

- `relevance_grade`: 0 무관 / 1 일부 도움 / 2 직접 필수 사실 근거. grade 2가 답변 전체를 충족한다는 뜻은 아니다.
- `evidence_spans`: 실제 chunk 본문에서 확인한 fact index, 문자 start/end(0-based, end-exclusive), 해당 문자열과 full/partial support.
- `fact_labels`: supported / partial / missing / not_retrieval_fact / unverified_corpus / source_review_pending.
- `passes_expected_filter=false`인 관련 문서는 본문 근거가 있어도 현재 Tool의 문서유형 filter로 검색되지 않을 수 있다. 필터 밖 양성 label도 보존한다.
- 구장 pool은 해당 구장의 모든 로컬 7월 chunk 문서 유형을 읽은 범위다. 복합 비교는 잠실·수원 두 구장이다. 다른 구장 및 DB의 공통 문서는 전체 탐색했다고 주장하지 않는다.
- URL이 `source_urls`에 있다는 것과 chunk 본문이 정확한 예매 URL·정책을 담는 것은 다르다. 본문에 없는 사실을 검색 성공으로 승인하지 않았다.
- 선호팀·선택 경기·추가 확인 안내 등의 동작 기대는 검색 Recall의 사실 분모와 분리한다. 합성 context와 출처 계약은 원래 evidence에 유지한다.
- 현재 local-labels1은 agent 검수이며 사람 검수는 아니다. `rank_metrics_ready=false`, `baseline_ready=false`를 유지한다.

### 실제 DB 확인이 필요한 이유

9월 11일 승격 문서에 고척 food/entry와 KBO 공통 반입 revision이 기록돼 있지만,
현재 로컬 embedded_input에는 본문이 없다. `historical_revision_hints`는 이 기록을
연결할 뿐, 현재 활성 상태나 relevance를 승인하지 않는다. 따라서 고척 음식물 등의
로컬 missing을 운영 corpus gap으로 단정하지 않는다. 야구지식도 공식 PDF 페이지
정답은 있어도 서비스 문서/chunk와 동일하다고 가정하지 않는다.

다음 단계는 사용자 승인 후 선택한 DB의 공개 `rag_documents`·`rag_chunks`만
읽기 전용으로 조회하여 활성 revision·본문·hash와 metadata filter를 대조하는 것이다.
DB 환경을 구분하고 local/production corpus가 다르면 별도 snapshot으로 기록한다.
사용자 대화·계정·인증정보는 조회 대상이 아니다. corpus 보강이나 migration은 이 단계에 포함하지 않는다.

### 사례별 로컬 결과

| 사례 | 검색 사실 포함 상태 | 부족하거나 미확인인 사실 |
|---|---|---|
| `golden_guide_001` | missing | 프로야구 음식물 반입 가능; 행사 성격별 제한; 재입장 음식물 반입 불가 |
| `golden_guide_002` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_003` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_004` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_005` | partial | 25인승 소형버스 이상·장애인 차량 예약 제외 |
| `golden_guide_006` | partial | 행사 취소로 주차요금 환불 안 됨 |
| `golden_guide_007` | partial | 구단별 예외·세부 정책 확인 |
| `golden_guide_008` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_009` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_010` | missing | 휴대용 의자 원칙적 제한; 구단 허용 구역 예외 가능 |
| `golden_guide_011` | missing | 내부 금연; 외부 지정 흡연 부스 |
| `golden_guide_012` | missing | 프로야구 분실물은 키움 관리; 키움 문의 |
| `golden_guide_013` | partial | 공식 편의시설 1층 내부 항목 |
| `golden_guide_014` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_guide_015` | missing | 36개월 미만 무료입장; 좌석 점유 시 티켓 구매; 증빙서류 지참 |
| `golden_ticket_001` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_ticket_002` | partial | ticket.ncdinos.com |
| `golden_ticket_003` | partial | ticket.ssg.com |
| `golden_ticket_004` | partial | www.ticketlink.co.kr |
| `golden_ticket_005` | missing | HANWHA 홈경기 공식 예매처: 티켓링크; www.ticketlink.co.kr |
| `golden_ticket_006` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_ticket_007` | missing | 부분취소 불가; 전체 취소 후 재예매; 기존 좌석 선점 보장 없음 |
| `golden_ticket_008` | partial | nol.yanolja.com; LG는 티켓링크로 홈팀별 예매처가 다름 |
| `golden_ticket_009` | source_review_pending | 미발권/발권 구분 및 구매수단별 환불 절차를 현재 공식 안내로 재확인; 상충하는 문구를 근거로 자동 환불이나 현장 환불을 확정하지 않음 |
| `golden_ticket_010` | partial | www.ticketlink.co.kr |
| `golden_knowledge_001` | unknown_local_knowledge_file_missing | 주자 존재; 투수 위반; 한 베이스 안전진루; 타자 1루 도달 및 다른 모든 주자 최소 한 베이스 진루 시 플레이 계속 |
| `golden_knowledge_002` | unknown_local_knowledge_file_missing | 무사 또는 1사; 1·2루 또는 만루; 쉽게 잡을 페어 플라이; 번트·직선타 제외; 타자 아웃·볼 인플레이 |
| `golden_knowledge_003` | unknown_local_knowledge_file_missing | 타자 출루로 점유권 상실; 포스 해제 후 신체 태그 필요 |
| `golden_knowledge_004` | unknown_local_knowledge_file_missing | 1루 비어 있음 또는 2아웃; 무사·1사 1루주자 존재 시 자동 아웃 |
| `golden_knowledge_005` | unknown_local_knowledge_file_missing | 외야 최초 낙하지점 기준; 이후 파울로 굴러도 페어 |
| `golden_knowledge_006` | unknown_local_knowledge_file_missing | 제3아웃 포스아웃은 득점 불인정 |
| `golden_knowledge_007` | unknown_local_knowledge_file_missing | 2스트라이크 번트 파울은 삼진; 포구된 번트 파울 플라이는 플라이 아웃 |
| `golden_knowledge_008` | unknown_local_knowledge_file_missing | 플레이 일시정지; 규칙상 허용 진루 구분 |
| `golden_knowledge_009` | unknown_local_knowledge_file_missing | 스트라이크 존 접촉은 스트라이크; 자동 1루 아님 |
| `golden_knowledge_010` | unknown_local_knowledge_file_missing | 투·포수 위반 볼; 타자 위반 스트라이크; 2026 KBO리그 기준 |
| `golden_knowledge_011` | unknown_local_knowledge_file_missing | 투구 위치 기반 볼·스트라이크; 체크스윙 별도 판단 |
| `golden_knowledge_012` | unknown_local_knowledge_file_missing | 보통 수비로 처리 가능 여부; 주자 진루; 폭투·포일 구분 |
| `golden_knowledge_013` | unknown_local_knowledge_file_missing | 무사 또는 1사; 주자 득점; 미포구 시 기록원 판단 |
| `golden_knowledge_014` | unknown_local_knowledge_file_missing | 타자 1루; 2루 단독 주자 강제 진루 아님 |
| `golden_knowledge_015` | unknown_local_knowledge_file_missing | 일반 판독과 별도 2회; 번트 시도 제외; 연장 1회 추가·번복 시 유지 |
| `golden_mixed_001` | partial | 쇼핑백 1개 30×50×12cm |
| `golden_mixed_002` | missing | ticket.ncdinos.com |
| `golden_mixed_003` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_mixed_004` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_mixed_005` | full | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_scope_001` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_scope_002` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_scope_003` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_scope_004` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |
| `golden_scope_005` | not_applicable | 필수 검색 사실 포함 또는 검색 평가 비대상 |


## 로컬 DB 확인 결과 — 2026-10-14 local-db1

사용자 승인 후 Supabase project `new-baseball`의 기존 로컬 컨테이너를 조회했다.
`BEGIN ... READ ONLY` transaction 안에서 공개 `rag_documents`·`rag_chunks`만
읽었고 `transaction_read_only=on`을 확인했다. 반복 읽기 snapshot과 별도 count
조회 결과는 동일하게 문서 0건, chunk 0건, 활성 문서 0건, embedding 보유 chunk 0건이다.
사용자/대화/Auth 테이블, API key, embedding 벡터는 조회하지 않았다.

이는 현재 로컬 환경의 확인 결과다. 과거 10월 6일 72개 chunk 기록이나 9월 운영
승격 기록이 지금 로컬 corpus를 증명하지 않는다. 운영 DB는 접속하지 않았다.

| 실제 로컬 DB 연결 상태 | 사례 수 |
|---|---:|
| 정답 근거를 담을 서비스 corpus가 비어 있음 | 43 |
| 삼성 환불 정답 보류 + corpus 비어 있음 | 1 |
| 검색 근거 연결 비대상 | 6 |
| 합계 | 50 |

후보 JSON의 `runtime_corpus_snapshot`에 빈 corpus manifest·hash·조회 범위를
저장했고, 각 사례의 `db_validation`에 동일 snapshot 연결과 missing fact index를
남겼다. `actual_matching_chunk_ids=[]`이며 현재 DB에 존재하지 않는 정답 ID를
만들지 않았다. 과거 revision hint는 현재 로컬 활성 상태가 false로 확인됐다.
기존 local-labels1의 7월 파일 근거 label은 비교 기록으로 보존한다.

데이터셋의 질문·공식 reference 후보는 유지한다. 실제 service chunk ID 연결,
검색 relevance 최종 고정, corpus freeze와 기준선 평가 준비는 아직 완료하지 못했다.
빈 환경 때문에 실패한 검색을 기존 서비스 검색 품질로 평가하지 않는다.
API·RAGAS·유료 embedding 호출이나 DB 적재·migration·reset은 하지 않았다.

다음 작업은 표준 source pipeline의 기존 corpus를 복구할 방법과 범위를 정하는 것이다.
로컬 seed에는 RAG corpus가 없고 현재 import script는 embedding API와 DB upsert를
사용하므로, seed 실행만으로 복구된다고 가정하지 않는다. 기존 embedding을 재사용할
수 있는 공개 corpus snapshot이 있는지 먼저 확인하고, 새 생성이 필요하면 비용을
산정한다. corpus 보강을 정답에 맞춰 수행한 뒤 과거 기준선으로 표현하지 않는다.
DB 쓰기·운영 DB 조회·유료 embedding은 각각 승인 범위를 확인한 뒤 수행한다.


## 운영 corpus 읽기 시도 — 2026-10-14

사용자가 운영 조회를 승인해 backend의 기존 설정을 비밀값 노출 없이 읽었다.
문서화된 운영 프로젝트와 PostgreSQL pooler/REST 대상이 같은 프로젝트인지 확인했다.
PostgreSQL은 tenant/user not found(SQLSTATE XX000), REST 호스트는 DNS 실패로
연결하지 못했다. 운영 dashboard도 로그인 페이지로 이동해 프로젝트 상태를 확인하지 못했다.
따라서 중지·삭제·주소 변경 중 어느 것이 원인인지는 확정하지 않는다.

운영 문서/chunk 건수와 snapshot hash는 null이다. 조회 실패를 0건으로 저장하지 않았다.
`production_corpus_check.status=connection_failed`, `read_completed=false`를 기록했다.
기존 local-db1 snapshot은 로컬 결과로만 유지한다. 운영 DB 변경·corpus 복사·유료
embedding·RAGAS는 수행하지 않았다. 운영 프로젝트 가용성 또는 현재 연결 설정을
확인해야 실제 문서·chunk의 읽기와 검색 정답 검수를 이어갈 수 있다.


## 운영 corpus 읽기 성공 — 2026-10-14 production-pool1

재활성화 후 운영 PostgREST GET 읽기가 성공했다. 공개 두 RAG 테이블과 embedding
존재 여부 목록을 각각 두 번 읽어 동일한 결과를 확인했다. SQL 원자적 transaction
snapshot은 아니며 그 제한을 `consistency`에 명시했다. PostgreSQL pooler로 접속이
복구됐다는 결과가 아니라, 기존 운영 REST 읽기 경로로 corpus를 확보한 결과다.

| 항목 | 건수 |
|---|---:|
| rag_documents | 72 |
| rag_chunks | 76 |
| 활성 문서 | 71 |
| 활성 문서에 속한 chunk | 75 |
| embedding 보유 chunk | 76 |
| 야구 지식 chunk | 27 |

고척 food/entry/bag r0001과 KBO 공통 반입 r0001이 실제로 존재한다. 비활성
문서는 이전 고척 bag legacy 문서 1개다. 초기 로컬 DB 0건은 운영 corpus의
누락 판정으로 사용하지 않는다. 로컬 환경에 데이터를 복사하거나 seed하지 않았다.

후보 JSON의 `production_corpus_snapshot`에 문서 상태와 chunk 본문·metadata의
hash manifest를 기록했다. 본문 전문은 임시 경로에만 보관하며 embedding 벡터와
사용자 데이터는 조회하지 않았다. `production_corpus_check`의 이전 연결 실패를
`read_complete`로 갱신했다. local-db1 결과는 로컬 snapshot으로 보존한다.

44개 RAG 대상(삼성 보류 포함)에 실제 운영 ID로 `production_candidate_pool`을
연결했다. 서비스 metadata filter·활성/승인 조건·embedding 존재 여부를 반영한
유한 pool이며, query embedding·유사도 threshold·top-k는 실행하지 않았다.
야구지식 retriever의 현재 SQL은 문서 활성 여부를 검사하지 않는다는 코드 조건도
그대로 반영했다. 비RAG 6개는 pool이 없다. multi 비교 사례는 두 구장 pool의 합집합이다.

이 연결은 실재 ID 확인이며 **각 chunk가 필수 사실을 뒷받침한다는 relevance
검수 완료가 아니다**. 다음은 운영 본문의 사실 span과 0/1/2 등급을 검수하는 것이다.
`rank_metrics_ready=false`, `baseline_ready=false`, `human_reviewed=false`를 유지했다.
DB 쓰기·LLM·embedding·RAGAS 평가는 하지 않았다.


## 운영 본문 relevance 검수 — 2026-10-14 production-labels1

현재 후보 버전은 `agent-golden-candidates-v1-draft-20261014-production-labels1`이다.
위 production-pool1의 ID 연결 단계에 이어, 고정한 운영 snapshot의 실제 본문을
필수 사실과 대조했다. 50개 모두 검수 상태를 기록했으며 사람이 승인한 최종
golden dataset은 아니다. `human_reviewed=false`, `frozen=false`,
`rank_metrics_ready=false`, `baseline_ready=false`, `evaluation_executed=false`를 유지한다.

| 필수 사실 근거 | 관련 corpus 본문 | 서비스 metadata 필터 적용 후 |
|---|---:|---:|
| 전체 근거 있음 | 20 | 18 |
| 일부 근거 있음 | 15 | 15 |
| 근거 없음 | 8 | 10 |
| 출처 확인 보류 | 1 | 1 |
| 검색 비대상 | 6 | 6 |
| 합계 | 50 | 50 |

이 숫자는 답변 정확도나 검색 성공률이 아니라 **필수 사실의 본문 포함 여부**다.
야구 지식은 현 corpus의 지식 chunk 27개를 문서 유형에 관계없이 검수했다.
구장/예매는 해당 구장과 공통 안내의 활성 chunk를 검수했다. 전체 corpus의
모든 무관한 chunk를 포함한 ranking 정답 집합은 아니다. 기존 로컬 구장 chunk
45개는 운영 본문과 동일함을 hash로 확인하고 사실 span 검수를 재사용했다.

`production_relevance_review`에 검수한 실제 ID, 문서 revision, 본문 hash,
0/1/2 등급, 사실별 근거 span의 문자 offset·hash를 저장했다. 2는 정답 사실의
직접 근거(일부 사실만 지원하는 경우 포함), 1은 관련 배경, 0은 해당 질문의
근거가 아닌 내용이다. 삼성 환불은 정답 보류이므로 등급도 null이다. 문서 제목이나
source URL만으로 정답 사실을 지원한다고 표시하지 않았다. 본문 전문은 Git에 저장하지 않았다.

주요 확인 사항:

- 제3아웃 득점은 `common_play_tag_out_force_out` 본문에 근거가 있지만
  사례의 `baseball_rule` 필터에서 제외되어 전체 근거 있음 → 근거 없음으로 바뀐다.
- 낫아웃의 일부 조건과 피치클락 제재도 다른 문서 유형에 있어 필터 적용 후
  근거가 줄어든다. 실제 검색 실행으로 검증한 결과는 아니다.
- 폭투·포일 정의, 희생플라이 조건, 체크스윙 판독 세부 조건 등은 문서가
  존재해도 해당 발췌 본문에 필요한 내용이 부족하다. 원문 발췌 범위를 검토해야 한다.
- 일부 구단 예매 URL·주차 예외·시설 위치는 공식 reference와 달리 운영 본문에
  빠져 있다. 삼성 우천 환불은 공식 안내 간 조건 차이가 있어 출처 검수를 유지한다.

검증 스크립트는 50개 구조·split·실재 ID·revision·hash·사실별 span 연결·필터
포함 여부·coverage 집계를 검사한다. `--production-snapshot`을 주면 임시 원문
snapshot에 대해 모든 본문 hash와 실제 span offset/hash도 검사한다.

다음 단계는 아래 보류/누락 항목과 기대답변의 사람 검수를 마치고, 평가에 사용할
범위 및 snapshot을 고정하는 것이다. corpus 보강은 별도 변경으로 기록하고
보강 전 기준선과 구분한다. 그 후 실제 agent 응답·검색 trace 수집과 RAGAS 평가를
진행한다. 이번 작업에서는 DB 쓰기·embedding·LLM·RAGAS 호출을 하지 않았다.

### 사례별 검수표

‘확인할 사실’에는 필터 적용 후 missing/partial인 기대 사실을 적었다.
질문·전체 기대답변·출처·chunk별 근거는 후보 JSON의 `input`, `expected`,
`evidence`, `retrieval_ground_truth.production_relevance_review`에서 확인할 수 있다.

| 사례 | 질문 | 본문 근거 | 필터 적용 후 | 확인할 사실 |
|---|---|---|---|---|
| golden_guide_001 | 고척돔 음식물 반입 가능해? | 일부 근거 있음 | 일부 근거 있음 | 행사 성격별 제한 |
| golden_guide_002 | 고척 야구 보러 가는데 내부 주차장에 차 대면 돼? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_003 | 사직구장 지하철 몇 호선 타고 어느 역에서 내려? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_004 | 잠실 야구 보러 가면 주차비가 항상 5분당 요금이야? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_005 | 수원 KT위즈파크는 경기일 주차 예약 없이 가도 돼? | 일부 근거 있음 | 일부 근거 있음 | 25인승 소형버스 이상·장애인 차량 예약 제외 |
| golden_guide_006 | 문학구장 승용차 주차 요금이 얼마고 경기 취소되면 돌려줘? | 일부 근거 있음 | 일부 근거 있음 | 행사 취소로 주차요금 환불 안 됨 |
| golden_guide_007 | 창원NC파크에 레이저 포인터 가져가도 돼? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_008 | 광주 챔필에 유리병 음료 들고 들어갈 수 있어? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_009 | 라팍에 뜨거운 국물 음식도 가져가도 되는 거야? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_010 | 대전 볼파크에 접이식 의자 가져가도 돼? 잔디석도 같아? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_011 | 고척돔 안에서 담배 피울 수 있어? | 근거 없음 | 근거 없음 | 내부 금연; 외부 지정 흡연 부스 |
| golden_guide_012 | 고척에서 야구 보다가 지갑 잃어버렸어. 어디에 문의해? | 근거 없음 | 근거 없음 | 프로야구 분실물은 키움 관리; 키움 문의 |
| golden_guide_013 | 대전 새 볼파크에 아기랑 가는데 수유실 있어? | 일부 근거 있음 | 일부 근거 있음 | 공식 편의시설 1층 내부 항목 |
| golden_guide_014 | 사직에서 유니폼 사려면 구장 어디로 가야 해? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_guide_015 | 잠실 LG 홈경기에 30개월 아기 데려가면 자리도 무료야? | 근거 없음 | 근거 없음 | 36개월 미만 무료입장; 좌석 점유 시 티켓 구매; 증빙서류 지참 |
| golden_ticket_001 | 사직 예매 어디서 해? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_ticket_002 | 우리 팀 경기 예매 방법 알려줘 | 일부 근거 있음 | 일부 근거 있음 | ticket.ncdinos.com |
| golden_ticket_003 | SSG 문학 홈경기 표 어디서 사? | 일부 근거 있음 | 일부 근거 있음 | ticket.ssg.com |
| golden_ticket_004 | KIA 광주 홈경기 예매 사이트 알려줘 | 일부 근거 있음 | 일부 근거 있음 | www.ticketlink.co.kr |
| golden_ticket_005 | 한화 대전 홈경기는 어디서 예매해? | 근거 없음 | 근거 없음 | HANWHA 홈경기 공식 예매처: 티켓링크; www.ticketlink.co.kr |
| golden_ticket_006 | LG 잠실 홈경기 일반 예매는 며칠 전 몇 시에 열려? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_ticket_007 | 키움 홈경기 표 4장 중 1장만 취소할 수 있어? | 근거 없음 | 근거 없음 | 부분취소 불가; 전체 취소 후 재예매; 기존 좌석 선점 보장 없음 |
| golden_ticket_008 | 두산 잠실 홈경기는 LG랑 같은 예매 사이트야? | 일부 근거 있음 | 일부 근거 있음 | nol.yanolja.com; LG는 티켓링크로 홈팀별 예매처가 다름 |
| golden_ticket_009 | 삼성 홈경기 우천취소면 발권한 표도 자동 환불돼? | 출처 확인 보류 | 출처 확인 보류 | 공식 환불 조건 충돌 확인 |
| golden_ticket_010 | KT 수원 홈경기 표는 티켓링크에서 예매하는 게 맞아? | 일부 근거 있음 | 일부 근거 있음 | www.ticketlink.co.kr |
| golden_knowledge_001 | 보크가 뭐야? | 일부 근거 있음 | 일부 근거 있음 | 타자 1루 도달 및 다른 모든 주자 최소 한 베이스 진루 시 플레이 계속 |
| golden_knowledge_002 | 인필드 플라이는 어떤 조건에서 선언되고 공을 놓치면 어떻게 돼? | 일부 근거 있음 | 일부 근거 있음 | 무사 또는 1사; 1·2루 또는 만루; 쉽게 잡을 페어 플라이; 번트·직선타 제외; 타자 아웃·볼 인플레이 |
| golden_knowledge_003 | 포스아웃이랑 태그아웃 차이가 뭐야? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_knowledge_004 | 낫아웃이면 1루에 주자가 있어도 무조건 뛸 수 있어? | 전체 근거 있음 | 일부 근거 있음 | 무사·1사 1루주자 존재 시 자동 아웃 |
| golden_knowledge_005 | 1루 지나 외야 페어 지역에 떨어진 공이 파울로 굴러가면 파울이야? | 근거 없음 | 근거 없음 | 외야 최초 낙하지점 기준; 이후 파울로 굴러도 페어 |
| golden_knowledge_006 | 3루 주자가 먼저 홈 밟았는데 마지막 아웃이 포스아웃이면 점수야? | 전체 근거 있음 | 근거 없음 | 제3아웃 포스아웃은 득점 불인정 |
| golden_knowledge_007 | 투스트라이크에서 번트가 파울이면 계속 치는 거야? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_knowledge_008 | 볼 데드 때는 주자가 마음대로 한 베이스씩 가도 돼? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_knowledge_009 | 몸에 맞으면 공이 스트라이크 존 안이어도 무조건 1루야? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_knowledge_010 | 2026 KBO 피치클락 투수랑 타자 위반하면 각각 어떻게 돼? | 일부 근거 있음 | 근거 없음 | 투·포수 위반 볼; 타자 위반 스트라이크 |
| golden_knowledge_011 | ABS가 체크스윙까지 자동으로 판정하는 거야? | 일부 근거 있음 | 일부 근거 있음 | 투구 위치 기반 볼·스트라이크 |
| golden_knowledge_012 | 폭투랑 포일은 어떻게 달라? | 일부 근거 있음 | 일부 근거 있음 | 보통 수비로 처리 가능 여부; 폭투·포일 구분 |
| golden_knowledge_013 | 희생플라이는 잡혀야만 기록돼? 놓쳐도 점수 나면 가능한가? | 일부 근거 있음 | 일부 근거 있음 | 무사 또는 1사; 주자 득점; 미포구 시 기록원 판단 |
| golden_knowledge_014 | 주자 2루만 있을 때 볼넷이면 그 주자도 3루로 가? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_knowledge_015 | 2026 KBO 체크스윙 판독은 일반 판독 기회를 써? 번트도 신청돼? | 근거 없음 | 근거 없음 | 일반 판독과 별도 2회; 번트 시도 제외; 연장 1회 추가·번복 시 유지 |
| golden_mixed_001 | 사직 처음 가는데 지하철이랑 가져가면 안 되는 가방 알려줘 | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_mixed_002 | 그럼 거기 경기 표는 어디서 사? | 근거 없음 | 근거 없음 | ticket.ncdinos.com |
| golden_mixed_003 | 그 경기 몇 시에 시작해? | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |
| golden_mixed_004 | 아니 이번엔 고척이야. 내부 주차는 가능해? | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_mixed_005 | 두산 잠실이랑 KT 수원 홈경기 예매처가 같은지 비교해줘 | 전체 근거 있음 | 전체 근거 있음 | 추가 누락 없음 / 검색 비대상 |
| golden_scope_001 | 오늘 고척 1루 쪽 표 몇 장 남았어? | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |
| golden_scope_002 | 우리 팀 홈경기 취소 수수료 얼마야? | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |
| golden_scope_003 | 사직에 유모차 맡기는 곳 위치 정확히 알려줘 | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |
| golden_scope_004 | 고척돔 콘서트도 야구 때처럼 음식물 들고 들어가면 돼? | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |
| golden_scope_005 | 야구 말고 내일 살 주식 하나 추천해줘 | 검색 비대상 | 검색 비대상 | 추가 누락 없음 / 검색 비대상 |


## 기대답변 최종 agent 검수 — 2026-10-14 final-review1

후보 버전 `agent-golden-candidates-v1-draft-20261014-final-review1`에서
질문·기대답변·필수 사실·출처·운영 본문 label의 연결을 검토했다.
49개를 탐색 평가 후보로 표시하고 삼성 환불 1개는 출처 보류로 유지했다.
이는 API runner 실행 준비 완료나 사람 승인 완료를 의미하지 않는다.
`final_review`에 사례별 검수 주체·날짜·탐색 후보 여부를 기록했다.
사람 검수 전 탐색 평가를 하더라도 agent 검수 후보라는 상태를 보고해야 한다.

기대답변에서 생략됐던 LG 아동 증빙서류와 복합 질문의 가방·쇼핑백 수치를
기존 필수 사실에 맞춰 명시했다. corpus 누락에 맞춰 정답을 축소하지 않았으며
DB 본문이나 서비스 검색 필터는 변경하지 않았다. 이전 검수 대기 메모는
당시 상태 기록으로 보존하고 최신 판정 필드를 구분했다.

삼성 안내는 다시 읽어도 발권 환불과 우천취소 현장 환불 불가 문구의 적용
범위가 불명확했다. 공식 티켓링크 상세 페이지는 접근 제한(ErrorCode:200)으로
추가 검증하지 못했다. 따라서 발권한 표의 자동 환불을 단정하거나 임의 정답을
만들지 않는다. reference 및 관련성 등급은 계속 null이다.

질문 50개와 제안 분할 35/15는 유지한다. 49개 중에서도 corpus gap은
측정 대상이며, scope 사례는 agent 동작만 평가한다. held_out은 튜닝 반복
실행에 쓰지 않는다. 정식 dataset freeze·RAGAS 평가 실행은 아직 하지 않았다.

### 질문 / 기대답변 / 출처 / 확인할 점

아래 기대답변은 source-backed 후보이며, 범위 밖·정보 부족 사례는 factual
정답 대신 기대 동작을 보여준다. 출처의 web bytes 미보관 제한은 기존 source
metadata에 유지한다. 숫자는 실제 검색 성능 점수가 아니다.

| 질문 | 기대답변 | 출처 | 확인할 점 |
|---|---|---|---|
| golden_guide_001 — 고척돔 음식물 반입 가능해? | 프로야구 때 음식물을 가져갈 수 있지만 행사별 제한이 있으며 재입장 때는 음식물 반입이 불가하다. | [gocheok_faq — 음식물 반입 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 운영 본문 부족: 행사 성격별 제한; 사람 검수 대기 |
| golden_guide_002 — 고척 야구 보러 가는데 내부 주차장에 차 대면 돼? | 프로야구 때 고척 내부 주차장은 이용 불가하며 대중교통 또는 인근 민영주차장을 확인한다. | [kiwoom_purchase — 티켓수령 및 입장 > 내부 주차장](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_003 — 사직구장 지하철 몇 호선 타고 어느 역에서 내려? | 롯데 공식 안내는 부산 도시철도 3호선 사직역 또는 종합운동장역을 안내한다. | [sajik_transport — 오시는 길 > 지하철](https://www.giantsclub.com/html/?pcode=207) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_004 — 잠실 야구 보러 가면 주차비가 항상 5분당 요금이야? | 평시 후불요금과 프로야구 선불제를 구분한다. 선불요금은 소형 6,000원·대형 12,000원이며 만차 시 입차가 제한될 수 있다. | [jamsil_parking — 평상시/프로야구 선불제, 기타사항](https://stadium.seoul.go.kr/about/park-info) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_005 — 수원 KT위즈파크는 경기일 주차 예약 없이 가도 돼? | 프로야구 경기일에는 일반 차량의 사전 주차예약이 필요하며 미예약 차량은 주차할 수 없다. 경기 시작 2시간 전부터 통제한다. 25인승 소형버스 이상과 장애인 차량은 예약 제외 대상으로 입차 시 요금을 납부한다. | [kt_parking — 주차예약 안내](https://www.ktwiz.co.kr/wizpark/parking) | 운영 본문 부족: 25인승 소형버스 이상·장애인 차량 예약 제외; 사람 검수 대기 |
| golden_guide_006 — 문학구장 승용차 주차 요금이 얼마고 경기 취소되면 돌려줘? | 승용차 전일 주차권은 2,000원이며 행사 취소 사유로 주차요금이 환불되지는 않는다. | [ssg_parking — 주차요금 > 행사 취소 환불 안내](https://www.ssglanders.com/stadium/parking) | 운영 본문 부족: 행사 취소로 주차요금 환불 안 됨; 사람 검수 대기 |
| golden_guide_007 — 창원NC파크에 레이저 포인터 가져가도 돼? | KBO 공통 안전정책은 레이저 포인터 반입을 제한한다. 방문 전 구단 안내도 확인한다. | [kbo_safe — FAQ 위험 물품 및 구단별 예외](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_008 — 광주 챔필에 유리병 음료 들고 들어갈 수 있어? | KBO 공통 안전정책은 유리병 반입을 제한하며 구단 세부 안내도 확인한다. | [kbo_safe — 안전·보안 규정 > 음료 용기](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_009 — 라팍에 뜨거운 국물 음식도 가져가도 되는 거야? | 금지품목이 아닌 음식은 허용 범위 내 반입할 수 있으나 뜨거운 국물 등 안전·관람환경을 해치는 음식은 제한될 수 있다. | [kbo_safe — FAQ 7 음식물](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_010 — 대전 볼파크에 접이식 의자 가져가도 돼? 잔디석도 같아? | 휴대용 의자는 원칙적으로 제한된다. 구단이 특별히 허용한 잔디석 등의 예외가 있을 수 있어 대전의 적용 여부는 확인해야 한다. | [kbo_safe — FAQ 6 휴대용 의자·잔디석 예외](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_011 — 고척돔 안에서 담배 피울 수 있어? | 경기장 내부는 금연이며 공식 안내의 외부 흡연 부스를 이용한다. | [gocheok_faq — 흡연 시설 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 운영 본문 부족: 내부 금연; 외부 지정 흡연 부스; 사람 검수 대기 |
| golden_guide_012 — 고척에서 야구 보다가 지갑 잃어버렸어. 어디에 문의해? | 프로야구 경기 때 분실물은 홈구단 키움이 수거·관리하므로 키움에 문의한다. | [gocheok_faq — 분실물 FAQ](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 운영 본문 부족: 프로야구 분실물은 키움 관리; 키움 문의; 사람 검수 대기 |
| golden_guide_013 — 대전 새 볼파크에 아기랑 가는데 수유실 있어? | 한화 공식 대전 볼파크 안내의 편의시설 탭에서 1층 내부 수유실을 확인할 수 있다. 세부 위치와 이용시간은 현장 안내를 확인한다. | [hanwha_facility — 편의시설 탭 > 1층 > 내부 > 수유실](https://www.hanwhaeagles.co.kr/MN/EP/MNEPPI01.do) | 운영 본문 부족: 공식 편의시설 1층 내부 항목; 사람 검수 대기 |
| golden_guide_014 — 사직에서 유니폼 사려면 구장 어디로 가야 해? | 롯데 공식 구장샵 안내는 유니폼샵을 사직 광장 1루측 컨테이너 1층, 프로페셔널샵을 구장 1층 중앙출입구 오른편으로 안내한다. | [sajik_shop — 유니폼샵·프로페셔널샵 위치](https://www.giantsclub.com/html/?pcode=367) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_guide_015 — 잠실 LG 홈경기에 30개월 아기 데려가면 자리도 무료야? | 36개월 미만은 무료입장이 가능하지만 별도 좌석이 제공되지 않는다. 좌석을 점유하려면 티켓을 구매해야 하며 나이를 확인할 증빙서류를 지참한다. | [lg_ticket — 미취학 아동 할인 및 관람 유의사항](https://www.lgtwins.com/ticket/general) | 운영 본문 부족: 36개월 미만 무료입장; 좌석 점유 시 티켓 구매; 증빙서류 지참; 사람 검수 대기 |
| golden_ticket_001 — 사직 예매 어디서 해? | 롯데 자체 예매(ticket.giantsclub.com)에서 해당 구단 홈경기를 확인한다. | [kbo_ticket — 예매처 > LOTTE](https://www.koreabaseball.com/kbo/league/map.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_ticket_002 — 우리 팀 경기 예매 방법 알려줘 | NC 자체 예매(ticket.ncdinos.com)에서 해당 구단 홈경기를 확인한다. | [kbo_ticket — 예매처 > NC](https://www.koreabaseball.com/kbo/league/map.aspx)<br>golden_ticket_002_fixture — golden_ticket_002.input 문맥·선호팀 | 운영 본문 부족: ticket.ncdinos.com; 사람 검수 대기 |
| golden_ticket_003 — SSG 문학 홈경기 표 어디서 사? | SSG 자체 예매(ticket.ssg.com)에서 해당 구단 홈경기를 확인한다. | [kbo_ticket — 예매처 > SSG](https://www.koreabaseball.com/kbo/league/map.aspx) | 운영 본문 부족: ticket.ssg.com; 사람 검수 대기 |
| golden_ticket_004 — KIA 광주 홈경기 예매 사이트 알려줘 | 티켓링크(www.ticketlink.co.kr)에서 해당 구단 홈경기를 확인한다. | [kbo_ticket — 예매처 > KIA](https://www.koreabaseball.com/kbo/league/map.aspx) | 운영 본문 부족: www.ticketlink.co.kr; 사람 검수 대기 |
| golden_ticket_005 — 한화 대전 홈경기는 어디서 예매해? | 티켓링크(www.ticketlink.co.kr)에서 해당 구단 홈경기를 확인한다. | [kbo_ticket — 예매처 > HANWHA](https://www.koreabaseball.com/kbo/league/map.aspx) | 운영 본문 부족: HANWHA 홈경기 공식 예매처: 티켓링크; www.ticketlink.co.kr; 사람 검수 대기 |
| golden_ticket_006 — LG 잠실 홈경기 일반 예매는 며칠 전 몇 시에 열려? | 일반 홈경기는 관람 7일 전 오전 11시부터 경기 시작 후 1시간까지 예매 가능하다. | [lg_ticket — 2026 티켓 예매 안내 > 예매 기간](https://www.lgtwins.com/ticket/general) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_ticket_007 — 키움 홈경기 표 4장 중 1장만 취소할 수 있어? | 부분취소는 불가하며 전체 취소 후 재예매해야 한다. 기존 좌석 확보는 보장되지 않고 취소 기한·수수료도 확인해야 한다. | [kiwoom_purchase — 예매취소 및 환불 > 부분취소](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do) | 운영 본문 부족: 부분취소 불가; 전체 취소 후 재예매; 기존 좌석 선점 보장 없음; 사람 검수 대기 |
| golden_ticket_008 — 두산 잠실 홈경기는 LG랑 같은 예매 사이트야? | NOL 티켓(nol.yanolja.com)에서 해당 구단 홈경기를 확인한다. LG 홈경기는 티켓링크이므로 홈팀을 구분한다. | [kbo_ticket — 예매처 > DOOSAN](https://www.koreabaseball.com/kbo/league/map.aspx) | 운영 본문 부족: nol.yanolja.com; LG는 티켓링크로 홈팀별 예매처가 다름; 사람 검수 대기 |
| golden_ticket_009 — 삼성 홈경기 우천취소면 발권한 표도 자동 환불돼? | 출처 충돌로 정답 보류 | [samsung_refund — 인터넷 예매/전화 예매 > 우천 취소](https://www.samsunglions.com/m/ticket/score_4_1_4.asp) | 삼성 발권/구매수단별 환불 절차 보류; 사람 검수 대기 |
| golden_ticket_010 — KT 수원 홈경기 표는 티켓링크에서 예매하는 게 맞아? | KBO 공식 예매처 안내에서 KT는 티켓링크에 속한다. | [kbo_ticket — 예매처 > 티켓링크 KT](https://www.koreabaseball.com/kbo/league/map.aspx) | 운영 본문 부족: www.ticketlink.co.kr; 사람 검수 대기 |
| golden_knowledge_001 — 보크가 뭐야? | 보크는 주자가 있을 때 투수의 규칙 위반에 대해 선고하며 원칙적으로 각 주자에게 한 베이스 안전진루권을 준다. 다만 타자가 안타·실책·4사구 등으로 1루에 도달하고 다른 모든 주자도 최소 한 베이스 진루하면 플레이가 계속된다. | [rules_2026 — 6.02(a) 본문·벌칙](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 타자 1루 도달 및 다른 모든 주자 최소 한 베이스 진루 시 플레이 계속; 사람 검수 대기 |
| golden_knowledge_002 — 인필드 플라이는 어떤 조건에서 선언되고 공을 놓치면 어떻게 돼? | 무사·1사에 1·2루 또는 만루, 쉽게 잡을 페어 뜬공이 대상이다. 번트·직선타는 제외되며 선고 시 타자 아웃, 볼은 인플레이다. | [rules_2026 — 용어 40; 5.09(a)(5)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 무사 또는 1사; 1·2루 또는 만루; 쉽게 잡을 페어 플라이; 번트·직선타 제외; 타자 아웃·볼 인플레이; 사람 검수 대기 |
| golden_knowledge_003 — 포스아웃이랑 태그아웃 차이가 뭐야? | 타자 출루로 밀려나는 주자는 포스 상태라 공을 가진 야수가 다음 베이스에 닿아 아웃시킬 수 있다. 포스가 풀리면 주자 신체 태그가 필요하다. | [rules_2026 — 용어 30·75; 5.09(b)(6)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_knowledge_004 — 낫아웃이면 1루에 주자가 있어도 무조건 뛸 수 있어? | 제3스트라이크 미포구 때 1루가 비었거나 2아웃이면 타자는 주자가 될 수 있다. 무사·1사에 1루주자가 있으면 타자 아웃이다. | [rules_2026 — 5.05(a)(2); 5.09(a)(3)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 무사·1사 1루주자 존재 시 자동 아웃; 사람 검수 대기 |
| golden_knowledge_005 — 1루 지나 외야 페어 지역에 떨어진 공이 파울로 굴러가면 파울이야? | 야수에게 먼저 닿지 않은 타구가 1루를 지난 외야 페어 지역에 처음 떨어졌다면, 이후 파울 지역으로 굴러가도 페어다. | [rules_2026 — 용어 25 FAIR BALL](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 외야 최초 낙하지점 기준; 이후 파울로 굴러도 페어; 사람 검수 대기 |
| golden_knowledge_006 — 3루 주자가 먼저 홈 밟았는데 마지막 아웃이 포스아웃이면 점수야? | 제3아웃이 포스아웃이면 먼저 홈을 밟았더라도 득점이 인정되지 않는다. | [rules_2026 — 5.08(a) 부기 (2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 제3아웃 포스아웃은 득점 불인정; 사람 검수 대기 |
| golden_knowledge_007 — 투스트라이크에서 번트가 파울이면 계속 치는 거야? | 포구되지 않은 번트 파울은 제3스트라이크로 아웃이다. 번트 파울 플라이가 포구되면 플라이 아웃이다. | [rules_2026 — 5.09(a)(4); 9.15(a)(4) 예외; 용어72](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_knowledge_008 — 볼 데드 때는 주자가 마음대로 한 베이스씩 가도 돼? | 볼 데드는 플레이가 일시정지된 상태로 임의 진루는 할 수 없다. 해당 규칙에 따라 안전진루권이 주어지거나 원래 베이스로 돌아가야 한다. | [rules_2026 — 용어20; 5.06(c)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_knowledge_009 — 몸에 맞으면 공이 스트라이크 존 안이어도 무조건 1루야? | 바운드하지 않은 투구가 스트라이크 존에서 타자에게 닿으면 스트라이크다. 몸에 맞았다는 이유만으로 1루가 주어지지 않는다. | [rules_2026 — 5.05(b)(2)(A)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_knowledge_010 — 2026 KBO 피치클락 투수랑 타자 위반하면 각각 어떻게 돼? | 2026 KBO리그에서 투·포수 위반에는 볼, 타자 위반에는 스트라이크가 부과된다. | [kbo_changes — 2026 피치클락 > 변경 사항](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 운영 본문 부족: 투·포수 위반 볼; 타자 위반 스트라이크; 사람 검수 대기 |
| golden_knowledge_011 — ABS가 체크스윙까지 자동으로 판정하는 거야? | ABS는 정규 투구의 위치를 추적해 볼·스트라이크 결과를 전달한다. 체크스윙 여부는 ABS 위치 판정과 구별한다. | [kbo_changes — ABS 운영 방식; 체크스윙 판독](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 운영 본문 부족: 투구 위치 기반 볼·스트라이크; 사람 검수 대기 |
| golden_knowledge_012 — 폭투랑 포일은 어떻게 달라? | 주자 진루를 초래한 투구에서 보통 수비로 처리 불가능하면 폭투, 처리 가능했는데 포수가 놓치면 포일로 기록한다. | [rules_2026 — 9.13(a)(b)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 보통 수비로 처리 가능 여부; 폭투·포일 구분; 사람 검수 대기 |
| golden_knowledge_013 — 희생플라이는 잡혀야만 기록돼? 놓쳐도 점수 나면 가능한가? | 무사·1사 때 외야의 플라이·직선타로 득점하면 기록될 수 있다. 놓쳤더라도 잡았어도 득점 가능했다고 기록원이 판단하면 해당한다. | [rules_2026 — 9.08(e)(1)(2)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 운영 본문 부족: 무사 또는 1사; 주자 득점; 미포구 시 기록원 판단; 사람 검수 대기 |
| golden_knowledge_014 — 주자 2루만 있을 때 볼넷이면 그 주자도 3루로 가? | 볼넷은 타자에게 1루를 주며 밀려나야 하는 주자만 강제 진루한다. 2루에만 있는 주자는 강제로 3루에 가지 않는다. | [rules_2026 — 5.05(b)(1)](https://6ptotvmi5753.edge.naverncp.com/KBO_FILE/ebook/pdf/2026_%EC%95%BC%EA%B5%AC%EA%B7%9C%EC%B9%99.pdf) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_knowledge_015 — 2026 KBO 체크스윙 판독은 일반 판독 기회를 써? 번트도 신청돼? | 체크스윙은 일반 판독과 별도로 팀당 2회 기회가 주어지며 번트 시도는 대상이 아니다. 연장전에는 1회 추가되고 번복되면 기회를 유지한다. | [kbo_changes — 체크스윙 비디오 판독 시행 세칙](https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx) | 운영 본문 부족: 일반 판독과 별도 2회; 번트 시도 제외; 연장 1회 추가·번복 시 유지; 사람 검수 대기 |
| golden_mixed_001 — 사직 처음 가는데 지하철이랑 가져가면 안 되는 가방 알려줘 | 부산 3호선 사직역·종합운동장역을 이용한다. KBO 공통 기준으로 1인 가방 1개(45×45×20cm)와 쇼핑백 1개(30×50×12cm)의 크기·개수 제한을 확인한다. | [sajik_transport — 오시는 길 > 지하철; SAFE 가방 크기·개수](https://www.giantsclub.com/html/?pcode=207)<br>[kbo_safe — 오시는 길 > 지하철; SAFE 가방 크기·개수](https://www.koreabaseball.com/Kbo/BusinessAndEvent/Safe.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_mixed_002 — 그럼 거기 경기 표는 어디서 사? | 선택된 창원NC파크의 NC 홈경기는 NC 자체 예매처 ticket.ncdinos.com에서 확인한다. | [kbo_ticket — 예매처 > NC](https://www.koreabaseball.com/kbo/league/map.aspx)<br>golden_mixed_002_fixture — golden_mixed_002.input 문맥·선호팀 | 운영 본문 부족: ticket.ncdinos.com; 사람 검수 대기 |
| golden_mixed_003 — 그 경기 몇 시에 시작해? | 고정된 합성 경기 문맥의 시작 시각인 18시 30분을 안내한다. | followup_contract — selected_game_time 분기<br>golden_mixed_003_fixture — selected_game.start_time | 검색 비대상: 동작 검수; 사람 검수 대기 |
| golden_mixed_004 — 아니 이번엔 고척이야. 내부 주차는 가능해? | 새로 명시한 고척을 기준으로, 프로야구 경기 때 내부 주차장 이용이 불가함을 안내한다. | [kiwoom_purchase — 내부 주차장 안내](https://heroesbaseball.co.kr/ticket/normal/viewPurchase.do)<br>golden_mixed_004_fixture — golden_mixed_004.input 문맥·선호팀 | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_mixed_005 — 두산 잠실이랑 KT 수원 홈경기 예매처가 같은지 비교해줘 | 두산은 NOL 티켓, KT는 티켓링크로 예매처가 다르다. | [kbo_ticket — 예매처 > 두산·KT](https://www.koreabaseball.com/kbo/league/map.aspx) | 본문 근거 있음; 실제 retrieval/답변 미실행; 사람 검수 대기 |
| golden_scope_001 — 오늘 고척 1루 쪽 표 몇 장 남았어? | 실시간 잔여석 조회 미지원 안내; 공식 예매처 확인 안내 | routing_contract — find_kbo_game 미지원 > ticket_inventory_tool_required | 검색 비대상: 동작 검수; 사람 검수 대기 |
| golden_scope_002 — 우리 팀 홈경기 취소 수수료 얼마야? | 선호 팀·선택 경기 없으면 구단 확인 질문 | routing_contract — search_ticketing_guide > 팀·구장 필수 입력 | 검색 비대상: 동작 검수; 사람 검수 대기 |
| golden_scope_003 — 사직에 유모차 맡기는 곳 위치 정확히 알려줘 | 구체적 위치 근거 없으면 확인 필요 안내; 공식 구단 문의 경로 안내 | [sajik_shop — 보존 구장샵 원문에는 유모차 보관 위치 근거 없음](https://www.giantsclub.com/html/?pcode=367) | 검색 비대상: 동작 검수; 사람 검수 대기 |
| golden_scope_004 — 고척돔 콘서트도 야구 때처럼 음식물 들고 들어가면 돼? | 행사별 음식물 제한 가능; 공연 주최 측 공지 확인 | [gocheok_faq — 음식물 FAQ > 행사 성격에 따른 제한](https://www.sisul.or.kr/open_content/skydome/community/faq.jsp) | 검색 비대상: 동작 검수; 사람 검수 대기 |
| golden_scope_005 — 야구 말고 내일 살 주식 하나 추천해줘 | 야구 서비스 범위 밖 안내 | scope_contract — 야구 범위 제한 | 검색 비대상: 동작 검수; 사람 검수 대기 |


## 재사용 수집 runner 준비 — 2026-10-14 runner1

[수집·입력 계획 도구](../../../backend/scripts/run_agent_golden_evaluation.py)는
고정 후보를 읽어 개발용 35개를 기본 선택한다. `--split all`로 50개를 포함한
미실행 계획을 출력할 수 있다. CLI는 `.env`를 읽거나 DB·API·judge를 호출하지
않는다. 실제 내부 graph 수집은 명시적으로 의존성을 주입한 Python 함수로
실행한다. 인증 HTTP·SSE·DB 저장 E2E runner는 별도 연결이 필요하다.
현재 dataset의 `baseline_ready=false`는 그대로 유지한다.

```bash
# 저장소 루트: 50개 모두 not_run으로 남기는 무호출 계획
backend/.venv/bin/python backend/scripts/run_agent_golden_evaluation.py \
  --split all \
  --output /private/tmp/agent-golden-plan-all.json

# 임시 합성 Capture JSONL을 읽어 텍스트 없는 요약·지표 입력 준비 여부를 출력
backend/.venv/bin/python backend/scripts/run_agent_golden_evaluation.py \
  --captures /private/tmp/agent-golden-captures.jsonl \
  --split development \
  --output /private/tmp/agent-golden-summary.json
```

`Capture`는 [별도 schema](schemas/agent_golden_capture.schema.json)로 검증한다.
Schema 재생성은 `--write-capture-schema`를 사용한다. 생성 답변·평가 입력 전문은
임시 Capture에만 두고 Git의 `runs/`에는 기준선·milestone 요약만 남긴다.
이번 무호출 계획은 평가 run으로 저장하지 않았다.

### 수집 경로와 입력 범위

`collect_graph_case`/`collect_graph_dataset`는 `BaseballAgentGraph`를 실행하는
`graph_factory(observer)`를 받는다. factory는 기존 routing/tool 의존성과
`AnswerGenerationService(evaluation_observer=observer.observe)`를 조립한다.
수집 함수가 환경·DB·judge를 자동 구성하지 않는다. 실제 수집 호출 전 환경,
코드/모델 설정, corpus snapshot 일치와 유료 budget·중단 정책을 호출자가
확정해야 한다. 온라인 evaluator는 이 내부 수집 경로에 구성하지 않는다.

- 원문 마지막 질문·날짜·선호 팀·compact conversation context를 그대로 전달한다.
- 이전 합성 history는 production graph가 받지 않으므로 이전 turn을 재생하지 않는다.
  고정 context만 주입하는 내부 graph 평가임을 adapter scope에 표시한다.
- 가상 선택 경기에는 메모리 전용 game ID를 넣는다. 실제 일정 조회 결과로 표현하지 않는다.
- RAGAS용 `user_input`은 원문 질문·날짜·선호 팀·고정 compact context를 담은 JSON이다.
  라우팅 query를 재작성하는 것이 아니며 기존 single-turn adapter와 scope가 다르다.
- 기본 development만 수집하며 held_out/all은 명시 선택한다. 삼성 환불은 수집 목록에서
  보류하되 전체 요약에 `not_run/source_review_pending`으로 남긴다.
- 복합 두 구단 비교는 현 single-tool agent 동작을 수집할 수 있으나 RAGAS 입력은
  `multi_tool_adapter_pending`으로 제외한다. 전체 질문 해결은 별도 검토한다.

### 정확한 근거와 실패 기록

검색 tool 결과의 `items` 순서를 보존한다. 생성기는 기존 정책대로 최대 3개·본문
6,000자 제한을 적용한다. 추가한 선택적 메모리 observer는 생성기에 **실제로 전달된**
request의 evidence와 계약 검증을 통과한 모델 답변을 source notice 추가 전에 받는다.
기존 SSE·DB metadata·온라인 평가에 이 observer 값을 추가하지 않았다.

생성 실패 시에도 실제 request 근거와 검색 결과를 남긴다. timeout·graph 오류는
원문 예외 대신 안정적인 reason code를 저장하며 자동 재시도하지 않는다.
후속 수집에서 각 사례를 1회 호출한다. source 보류·미실행도 요약 분모에 유지한다.

요약에는 답변·검색 결과·generation evidence의 hash만 남긴다. routing/filter 일치,
응답 origin, 미실행·제외 사유와 null 점수를 기록한다. `completed`는 graph 완료만
뜻하며 `question_resolution=not_judged`, SSE·저장=`not_checked`다. 토큰·비용을
관측하지 않았다면 null이며 비용 0으로 채우지 않는다. runtime 코드·모델 설정과
전체 runtime corpus 검증도 아직 null/false다. dataset 작성 때의 revision이나
본문 label snapshot을 실제 실행환경 검증으로 표현하지 않는다.

### 순위 지표와 RAGAS 입력 계획

`Recall@3/5`와 `MRR@3/5`는 등급 2인 핵심 chunk, `nDCG@3/5`는 0/1/2 gain을
사용한다. 사례의 expected filter 유한 pool 기준이며 corpus 전체 Recall이 아니다.
반환된 chunk 본문 hash가 고정 snapshot과 다르거나 ID가 미검수/필터 밖이면 제외한다.
중복 반환도 제외한다. 필터 안 핵심 근거가 없으면 corpus gap으로 제외하고, 핵심
근거가 있는데 정상 검색 결과가 비었다면 실제 rank 값 0을 기록한다. 반환 본문
hash 검사만으로 전체 runtime corpus가 동일하다고 주장하지 않는다.

RAGAS 입력은 기존 `EvaluationSample`·`prepare_metric_inputs`를 재사용한다.
reference provenance는 `agent_reviewed_candidate_not_human`으로 표시한다.
adapter의 `approved`는 이 탐색용 agent source review를 뜻하며 dataset의
`human_reviewed=false`를 승격하지 않는다. 생성 실패에서도 검색 근거가 있으면
context 지표 입력 준비는 가능하다. 실제 score는 judge를 호출하지 않아 null이다.
모델 원출력 capture가 없으면 최종 문자열을 잘라 복원하지 않고 제외한다.

다음 실행 단계에는 인증 API·SSE·저장 확인 연결, 단계별 usage·비용 수집,
런타임 corpus/code/model 설정 확인, 유료 budget guard와 judge 호출 연결이 필요하다.
현재 내부 graph 합성 검증 결과를 운영 기준선이나 RAGAS 품질 점수로 사용하지 않는다.

### runner1 검증 결과

- 새 runner 테스트 16개: 원문·고정 context, 실제 graph 근거 분리, source notice 전
  답변, contextual direct, fallback, timeout, source 보류·분할, 본문 drift/중복,
  corpus gap/정상 빈 검색의 구분, 요약의 본문 미저장 확인.
- Python 3.13.1 + `uv.lock` 의존성의 임시 환경에서 전체 backend 테스트 **157 passed**.
  테스트는 mock/injected 의존성을 사용하며 실제 DB·유료 API·judge를 호출하지 않았다.
- 기존 Python 3.14 환경에는 RAGAS가 없었고 잠긴 `scikit-network`를 빌드하는 데
  실패했다. 저장소 lock/model 설정을 바꾸지 않고 문서 기준 Python 3.13 환경을
  `/private/tmp/baseball-golden-runner-py313`에 만들어 전체 검증했다.
- 새 후보/기존 chat 데이터 validator, 변경 Python 파일 Ruff/format 및
  `git diff --check` 통과. 무호출 전체 계획 50개는 captured=0, 모두 not_run이다.


## 평가 실행 설정 준비 — 2026-10-14 runtime1

첫 평가 공통 예산은 2026-10-15 사용자 요청으로 **총 US$2.50**로 변경했다.
목표는 현재 agent 구성을 실제 테스트해 수준을 보여주는 것이며, 개선 전 기준선을 측정한다.
[실행 설정](configs/agent_golden_baseline_v1.json)을 만들었으며 `live_execution_enabled=false`다.
예산 승인은 DB 쓰기·평가 계정 생성 승인과 구별한다. 현재 환경은 원격 DB 대상,
provider key 설정 있음, routing/answer `gpt-5-mini` 일치로 확인했다. 비밀값은 출력하지
않았다. 4000번 서버의 listening process는 없었다. 기존 `.env`는 수정하지 않았다.

| 항목 | 설정 |
|---|---|
| 전체 공통 예산 | US$2.50, routing + answer + embedding + judge |
| 우선 분할 | development 35개; held_out/all은 별도 명시 선택 |
| 반복·동시 실행 | 사례당 1회, 순차 1개, SDK/judge retry 0 |
| routing / answer | 기존 gpt-5-mini |
| answer reasoning | 구장·예매 low, 야구 지식 medium (현재 서비스 분기) |
| 검색·judge embedding | text-embedding-3-small |
| RAGAS judge | gpt-4o-mini-2024-07-18, temperature 0 |
| 제한 | routing 출력 2,048 / answer 4,096 / judge 2,048 tokens |
| 시간 | provider 30초 / answer 15초 / turn 60초 / judge 30초 |
| 평가 프로세스 | online 평가 off, API 응답 로그 off, SQL debug off |
| 실 실행 | off; 평가 계정·DB 저장 대상 승인 대기 |

출력 상한·retry 0은 평가 비용을 제한하기 위해 명시한 설정이다. 원래 서비스의
무상한 출력·SDK 기본 retry 설정과 다르므로 추후 run에 설정 차이를 반드시 남긴다.
모델·원문 질문·생성 prompt·tool 제한을 임의로 바꾸지 않는다.

가격은 2026-10-14 공식 모델 페이지에서 확인했다. 100만 tokens당 비캐시 input/output은
[gpt-5-mini](https://developers.openai.com/api/docs/models/gpt-5-mini) $0.25/$2.00,
[gpt-4o-mini](https://developers.openai.com/api/docs/models/gpt-4o-mini) $0.15/$0.60,
[text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small) $0.02다.
캐시 할인·Batch 할인·다른 service tier를 가정하지 않는다. 모델 페이지의 deprecated
표시는 확인했으나 기존 baseline 모델을 교체하지 않았다. 이 계정에서 실제 모델을
호출할 수 있는지는 유료 실행 전 확인 대상이며 설정 존재와 구별한다.

### 설정 검증과 전용 프로세스

```bash
# 저장소 루트: 설정 + 비밀값 없는 환경 점검, 네트워크/DB/API 호출 없음
backend/.venv/bin/python backend/scripts/agent_evaluation_runtime.py \
  --config data/chat/evaluation/configs/agent_golden_baseline_v1.json \
  --check-env
```

[환경 overlay 예시](../../../backend/evaluation.env.example)는 전용 평가 프로세스에서
app 모듈을 import하기 전에 환경변수로 적용한다. 일반 `.env`에 덮어쓰지 않는다.
Schema는 [runtime schema](schemas/agent_evaluation_runtime.schema.json)를 사용한다.
`--write-schema`로 재생성한다. 이 점검 CLI는 서버를 시작하거나 실제 수집을 하지 않는다.

`EvaluationResources`가 별도 HTTP client 4개와 하나의 `RunBudget`을 구성한다.
routing/answer service에는 budget transport·output cap·retry 0을 명시적으로 주입하고,
embedding handler에는 `embedding_client`, RAGAS에는 `metrics()`의 budgeted judge를
주입해야 한다. 일반 앱의 cached OpenAI client로 우회하면 이 공통 한도가 적용되지
않으므로 평가 서버의 의존성 조립에서 모든 client를 이 resources로 연결해야 한다.
client 생성·metric 생성 자체는 유료 호출이 아니다. 끝날 때 `aclose()`로 정리한다.

### 예산 중단 규칙

`BudgetTransport`는 실제 요청 직전에 모델·endpoint·출력 상한·standard tier·공개
text 입력을 검사한다. 직렬화 request bytes+framing을 input token의 보수적 상한으로,
출력 token cap을 output 상한으로 예약한다. 음성·이미지·미가격 모델·상한 없는 요청은
보내지 않는다. 이 예약액은 실제 청구액 측정치가 아니다.

공통 ledger는 Git 제외 경로 `backend/logs/evaluation/agent-golden-first-baseline-v1-budget.json`에
run ID·한도·예약액·요청 수·중단 상태만 저장한다. 파일 lock과 fsync로 여러 client가
공유하며, 재시작·실패·취소로 예약액을 반환하거나 한도를 초기화하지 않는다.
한도가 부족하면 해당 요청 전 중단하고 중단 상태를 보존한다. 훼손·한도 불일치도
실패로 처리한다. ledger를 삭제하거나 새 run ID로 만들면 예산이 초기화되므로 승인된
첫 평가의 ledger를 보존해야 한다. OS/파일 삭제까지 방지하는 외부 billing limit은 아니다.

`collect_graph_dataset(stop_requested=lambda: resources.budget.stopped)`로 후속 사례를
중단하고 `summarize(..., not_run_reason='budget_stopped')`로 미실행 분모를 보존한다.
실제 usage 없는 실패 호출은 cost 0으로 저장하지 않는다. 모든 50개 지표가 $2.50 안에서
완료된다는 보장은 없으며, 예산 도달 시 미측정 사유를 남기는 것이 실행 계약이다.

### 인증·SSE·저장 확인 연결

[API 확인 adapter](../../../backend/scripts/agent_evaluation_api.py)는 주입된 인증 client만
사용한다. `prepare_api_fixture`는 write 승인·전용 합성 계정·날짜·선호 팀 일치를
확인한 뒤 새 합성 대화의 `agent_context`만 준비한다. 일반 사용자 프로필을 수정하지
않는다. 팀 fixture 불일치는 호출 전에 해결해야 한다. 이 준비 함수는 실제 호출 시 DB
쓰기이므로 이번 설정 작업에서 호출하지 않았다.

`collect_api_case`는 마지막 원문 질문을 1회 POST하고 `assistant.delta`의 조합,
`assistant.completed`, 동일 대화의 `done`, `stream.failed` 여부를 확인한다.
해당 대화의 messages만 재조회해 assistant ID·content·completed 상태와 원문 user
메시지를 대조한다. 전체 사용자 대화 목록을 수집하지 않는다. 영구 `ApiCheck`에는
본문·cookie·token·user/conversation/message ID를 저장하지 않는다. 인증 실패·SSE
중단·delta 불일치·저장 불일치를 각각 구분한다.

현재 공개 SSE에서는 model 원답변·실제 generation request를 제공하지 않으므로
`model_capture=not_available_from_public_sse`다. 동일 API 요청의 내부 observer capture를
메모리로 연결해야 RAGAS 입력이 된다. 내부 graph를 별도로 재실행한 답변을 API 요청의
답변으로 합치거나 최종 문자열을 잘라 원답변으로 만들지 않는다.

### 인증·SSE·저장 경로의 남은 실행 조건

설정·budget transport·API 확인 함수는 준비됐지만 runtime-ready는 아직 false다.
전용 평가 계정, DB 쓰기 대상 승인, budgeted 의존성으로 조립한 평가 서버,
동일 API 요청의 내부 capture 연결 및 runtime corpus hash 확인이 남아 있다.
이 조건이 충족되기 전 이 인증·SSE·저장 경로의 평가를 시작하지 않는다.

runtime1 검증: 예산·API adapter 테스트 20개와 기존 테스트를 포함해 Python 3.13
환경의 전체 **177개 테스트 통과**. 실제 SDK의 routing/answer/embedding 요청을
mock HTTP로 흘려 공통 ledger 예약·출력 cap 전달을 확인했다. 인증 실패, SSE
중단, delta 불일치, 저장 불일치, fixture mismatch, 재시작·동시 예산 예약·중단
상태 보존·훼손 ledger 거부도 검증했다. 실제 DB 쓰기나 유료 요청은 0회다.

### 2026-10-15 읽기 전용 실제 평가 완료

사용자가 운영 DB 쓰기를 제외한 agent 평가를 선택하여 실제 graph·운영 pgvector·
RAGAS 기준선을 실행했다. 위의 0회 기록은 runtime1 설정 검증 시점의 기록이다.
이번 실행은 50건 중 49건 1회 실행, 출처 보류 1건, provider 요청 545회,
DB 쓰기 0회다. 공통 한도 $2.50 안에서 사전 예약액 $2.328155로 완료했다.
관측 usage와 usage 미확인 timeout 예약액을 합친 비용 상한 추정은 $0.48053323이다.
인증·SSE·저장은 미검증이며, 사람 검수 전 후보 데이터셋을 사용했다.

[결과 해석 보고서](../../../docs/work/2026-10-15-agent-golden-readonly-baseline.md)와
[실제 실행 JSON](runs/ragas/2026-10-15-agent-golden-readonly-baseline-v1.json)에
지표별 분모, 미측정 사유, agent 사실 대조 검토, 비용과 실행 범위를 기록했다.
Answer relevancy 입력 직렬화와 자동 Context recall 과대평가 사례가 있어
자동 점수를 전체 정답률로 해석하지 않는다. 평가 전후 전체 corpus manifest는 일치했다.
