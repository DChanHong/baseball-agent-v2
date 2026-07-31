# Baseball Knowledge RAG Data And Embedding Plan v1-1

> 작성일: 2026-07-31  
> 대상 Tool: `search_baseball_knowledge`  
> 목적: KBO 공식 PDF와 최신 규정 웹페이지를 기반으로 야구 지식 RAG 데이터를 수집, 정제, 임베딩하기 위한 계획  
> 상태: 계획 수립 단계

## 1. Tool 목표

`search_baseball_knowledge`는 KBO 직관 도우미가 기본 야구 규칙, 자주 헷갈리는 플레이, KBO 리그 최신 적용 규칙을 근거 기반으로 설명할 수 있게 하는 RAG Tool이다.

초기 Tool 범위:

```text
기본 경기 규칙
자주 헷갈리는 플레이
KBO 리그 최신 적용 규칙
```

초기 제외 범위:

```text
야구장 관람 가이드북
기록/스탯 심화 설명
KBO 연감
레코드북
기록대백과
선수/팀 히스토리
구장별 관람 정보
```

## 2. 원본 데이터 원칙

PDF 원본은 용량이 크고 재배포 필요가 없으므로 git에 포함하지 않는다. 필요할 때 사용자가 로컬 PDF 경로를 제공하고, 추출 산출물만 repo의 데이터 파이프라인에 맞게 관리한다.

현재 로컬 원본 경로:

```text
/Users/hong/Desktop/야구지식-RAG용
```

현재 확인된 PDF:

| 파일명 | 문서 유형 | 연도 | 페이지 수 | 용도 |
|---|---:|---:|---:|---|
| `2024_야구규칙.pdf` | 공식야구규칙 | 2024 | 212 | 과거 규칙 비교, 변경점 확인 |
| `2025_야구규칙.pdf` | 공식야구규칙 | 2025 | 220 | 과거 규칙 비교, 변경점 확인 |
| `2026_야구규칙.pdf` | 공식야구규칙 | 2026 | 220 | 최신 기본 규칙 1차 근거 |
| `2024_리그규정.pdf` | KBO 리그 규정 | 2024 | 102 | 과거 리그 적용 규칙 비교 |
| `2025_리그규정.pdf` | KBO 리그 규정 | 2025 | 102 | 과거 리그 적용 규칙 비교 |
| `2026_리그규정.pdf` | KBO 리그 규정 | 2026 | 106 | 최신 KBO 적용 규칙 1차 근거 |

PDF 상태:

```text
암호화 없음
PDF outline/bookmark 없음
텍스트 추출 가능
일부 표지/앞쪽 페이지는 텍스트 없음
일부 한글 인코딩 경고가 있으므로 추출 결과 검수 필요
```

## 3. Source 우선순위

1. `2026_야구규칙.pdf`
   - 기본 경기 규칙과 판정 정의의 최신 1차 근거다.
2. `2026_리그규정.pdf`
   - KBO 리그 운영과 공식야구규칙 위에 적용되는 최신 리그 규정 근거다.
   - 문서상 공식야구규칙과 상이할 때 리그 규정이 우선한다.
3. `2024~2025` PDF
   - 최신 규칙과의 비교, 변경점 확인, 섹션 추출 안정성 검증에 사용한다.
4. KBO 주요 규정/규칙 웹페이지
   - PDF 반영 전후 최신 변경 요약 보조 출처로 사용한다.
   - 예: ABS, 피치클락, 체크스윙 판독, 3피트 주로, 포스트시즌 우천 규정.

## 4. PDF별 추출 계획

### 4.1 공식야구규칙 PDF

최신 기준 문서: `2026_야구규칙.pdf`

주요 목차 구조:

| 장 | 제목 | MVP 활용 |
|---|---|---|
| `1.00` | 경기의 목적 | 야구의 정의, 공격/수비 목적, 득점 기본 |
| `4.00` | 경기의 준비 | 더블헤더, 경기장 사용 결정권 일부 |
| `5.00` | 경기의 진행 | 볼/스트라이크, 타자, 주자, 투수, 볼 인플레이/데드 |
| `6.00` | 부적절한 플레이, 금지행동, 비신사적 행위 | 방해, 업스트럭션, 보크, 타자/투수 반칙 |
| `7.00` | 경기의 종료 | 정식경기, 일시정지 경기, 몰수/제소, 우천 맥락 |
| `9.00` | 공식기록원 | 희생플라이/희생번트, 폭투/패스트볼, 더블플레이 등 최소 보조 |

2026 PDF 기준 우선 추출 페이지:

| topic_id | 주제 | 우선 페이지 | 보조 페이지 | 비고 |
|---|---|---:|---|---|
| `basic_rule_game_objective` | 야구의 목적, 공격/수비 목적 | 25 | 21 | 초보자용 첫 설명 |
| `basic_rule_scoring` | 득점 조건 | 25, 47 | 21, 45 | 득점과 주자 귀루/진루 구분 |
| `basic_rule_strike_ball` | 볼/스트라이크 | 49-52 | 24 | ABS 설명은 리그규정으로 보강 |
| `basic_rule_fair_foul` | 페어/파울 | 26-27, 37 | 12-15 | 타구 판단 중심 |
| `basic_rule_out_count` | 아웃의 의미와 아웃 상황 | 37, 45-47 | 22, 24 | 초보자 설명으로 재작성 |
| `basic_rule_runner_advance` | 주자 진루와 귀루 | 53-65 | 22, 25 | 전체 규정이 길어 핵심만 추출 |
| `basic_rule_live_dead_ball` | 볼 인플레이/볼 데드 | 45-48 | 25 | 플레이 중단 상황 설명 |
| `basic_rule_regular_game` | 정식경기, 노게임 기본 | 136-139 | 17-18, 95-96 | 리그규정 우천 항목으로 보강 |
| `basic_rule_suspended_game` | 일시정지 경기 | 208 | 136-139 | KBO 리그규정과 충돌 여부 확인 |
| `common_play_balk` | 보크 | 50, 57, 64, 66-67 | 45 | 리그규정 피치클락/투구 제한 보강 |
| `common_play_infield_fly` | 인필드 플라이 | 75, 77, 83-84 | 158, 169 | 초보 질문 빈도 높음 |
| `common_play_tag_out_force_out` | 태그아웃/포스아웃 | 53, 56, 58, 62, 70, 73, 80-83 | 77-79 | 비교 설명 필요 |
| `common_play_steal_pickoff` | 도루, 견제 | 55, 58, 64, 82, 113 | 23 | 견제는 피치클락과 함께 보강 |
| `common_play_sacrifice` | 희생번트, 희생플라이 | 151, 153, 155-156 | 23, 47 | 기록 파트에서 최소 추출 |
| `common_play_double_play` | 병살, 더블플레이 | 147 | 37, 45 | 기록 파트 보조 |
| `common_play_wild_pitch_passed_ball` | 폭투/포일 | 129, 131, 153 | 50, 62-63 | PDF 용어 `패스트볼`은 passed ball 의미 |

2024/2025 PDF 사용 방식:

```text
동일 topic_id별로 2024, 2025, 2026 텍스트를 비교한다.
검색 결과 기본 노출은 2026 최신 chunk를 우선한다.
과거 연도는 변경점 확인 또는 추출 품질 검증용 metadata로 유지한다.
```

### 4.2 KBO 리그 규정 PDF

최신 기준 문서: `2026_리그규정.pdf`

주요 목차/섹션:

| 조항/영역 | 제목 | MVP 활용 |
|---|---|---|
| 제27조 | 기상 상황으로 인한 경기취소 여부 | 우천 취소 권한과 한계 |
| 제28조 | 비디오 판독 | 판독 대상, 절차, 체크스윙 판독 |
| 제63조 | 천재지변 등의 사유로 인한 일정취소 조치 | 일정 취소/재편성 맥락 |
| 제66조 | 경기거행 여부 결정 권한 이관 시점 | 경기 전/후 결정 주체 |
| KBO ABS 규정 | 자동 볼-스트라이크 판정 | 최신 스트라이크/볼 적용 |
| KBO 피치클락 규정 | 투구 간 시간 제한 | 투수/타자 제한, 견제/보크 맥락 |

2026 PDF 기준 우선 추출 페이지:

| topic_id | 주제 | 우선 페이지 | 보조 페이지 | 비고 |
|---|---|---:|---|---|
| `latest_rule_video_review` | 비디오 판독 | 29-32 | 8, 12 | 판독 가능 항목과 한계 |
| `latest_rule_check_swing_review` | 체크스윙 판독 | 12, 29-32 | KBO 웹페이지 | 2026 변경 요약과 함께 검증 |
| `latest_rule_abs` | ABS | 67-69 | 10, 12 | 볼/스트라이크 질문의 최신 보강 |
| `latest_rule_pitch_clock` | 피치클락 | 70-78 | 10, 12 | 견제, 보크, 경기 흐름 질문 보강 |
| `latest_rule_weather_cancel` | 기상 상황 경기취소 | 44-46 | 14-15, 20-21 | 날씨 Tool과 경계 필요 |
| `latest_rule_no_game_suspended` | 노게임/서스펜디드 | 24, 45-52, 61 | 14-15 | 공식야구규칙 7.00과 함께 설명 |
| `latest_rule_game_authority` | 경기거행 여부 결정 권한 | 48-49 | 44-46 | 취소 확정 답변 금지 정책과 연결 |
| `latest_rule_three_foot_lane` | 3피트 주로 | 2026 주요 규정 웹페이지 | 리그규정 키워드 추가 확인 | PDF 페이지 재확인 필요 |

2024/2025 PDF 사용 방식:

```text
비디오 판독, ABS, 피치클락, 우천/서스펜디드 관련 변경점 확인에 사용한다.
사용자 답변에는 최신 규정 우선, 과거 문서는 필요 시 "연도별 규정 차이" 질문에만 사용한다.
```

## 5. 보조 웹페이지 수집 계획

대상:

```text
KBO 주요 규정/규칙 최신 시즌 페이지
예: https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx
```

수집 목적:

```text
PDF보다 읽기 쉬운 최신 변경 요약 확보
ABS, 피치클락, 체크스윙 판독, 3피트 주로 등 변경 포인트 보강
PDF section chunk와 같은 topic_id로 연결
```

저장 방식:

```text
data/baseball_knowledge/raw/web/YYYY-MM-DD/kbo_game_manage_2026.html
data/baseball_knowledge/normalized/latest_rules_2026.json
```

## 6. 데이터 디렉터리 계획

PDF 원본은 repo 밖에 두고, repo에는 추출/정제 산출물만 둔다.

```text
data/baseball_knowledge/
├── README.md
├── sources.json
├── raw/
│   ├── extracted_pdf/
│   │   └── 2026/
│   │       ├── official_baseball_rules_pages.jsonl
│   │       └── league_rules_pages.jsonl
│   └── web/
├── normalized/
│   ├── basic_rules.json
│   ├── common_plays.json
│   └── latest_kbo_rules.json
├── embedded_input/
│   └── baseball_knowledge_chunks.jsonl
└── evaluation/
    ├── cases/
    └── runs/
```

## 7. Chunk 설계

초기에는 topic 단위 curated chunk를 기본으로 한다. PDF 원문 section chunk는 감사/검증용으로 유지하고, 실제 검색 결과는 초보자용으로 재작성된 curated chunk를 우선 임베딩한다.

Chunk schema 초안:

```json
{
  "schema_version": "1.0.0",
  "chunk_id": "baseball_knowledge_basic_rule_strike_ball_2026_chunk_000",
  "document_id": "baseball_knowledge_basic_rule_strike_ball_2026",
  "chunk_index": 0,
  "document_type": "baseball_rule",
  "knowledge_type": "basic_rule",
  "topic_id": "basic_rule_strike_ball",
  "title": "볼과 스트라이크",
  "season_year": 2026,
  "is_latest": true,
  "as_of": "2026-07-31",
  "trust_level": "official",
  "review_status": "needs_review",
  "source_ids": ["kbo_2026_official_baseball_rules"],
  "source_urls": ["..."],
  "source_pages": [{"source_id": "kbo_2026_official_baseball_rules", "pages": [49, 50, 51, 52]}],
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "embedding_text": "제목: 볼과 스트라이크\n지식유형: basic_rule\n핵심주제: ...\n본문:\n...",
  "content": "...",
  "content_hash": "...",
  "metadata": {
    "language": "ko",
    "audience": "beginner",
    "source_file_external": "2026_야구규칙.pdf",
    "limitations": []
  }
}
```

검색 품질을 위해 `embedding_text`에는 다음 정보를 포함한다.

```text
제목
지식유형
topic_id
동의어/검색키워드
초보자 질문 예시
본문
출처 문서명과 페이지
```

## 8. MVP Topic 목록

### 기본 경기 규칙

```text
basic_rule_game_objective
basic_rule_scoring
basic_rule_strike_ball
basic_rule_fair_foul
basic_rule_out_count
basic_rule_runner_advance
basic_rule_live_dead_ball
basic_rule_regular_game
basic_rule_suspended_game
```

### 자주 헷갈리는 플레이

```text
common_play_balk
common_play_infield_fly
common_play_tag_out_force_out
common_play_steal_pickoff
common_play_sacrifice
common_play_double_play
common_play_wild_pitch_passed_ball
```

### KBO 최신 적용 규칙

```text
latest_rule_video_review
latest_rule_check_swing_review
latest_rule_abs
latest_rule_pitch_clock
latest_rule_weather_cancel
latest_rule_no_game_suspended
latest_rule_game_authority
latest_rule_three_foot_lane
```

초기 목표 chunk 수:

```text
20~30 curated chunks
필요 시 topic당 2024/2025/2026 source 비교 metadata 보강
```

## 9. 임베딩 및 DB 계획

기존 `search_stadium_guide`와 같은 `rag_documents`, `rag_chunks` 테이블을 재사용할 수 있다. 다만 현재 테이블에는 `stadium_id`, `team_id`가 nullable이므로 baseball knowledge chunk는 두 값을 `null`로 둔다.

필요한 검토:

```text
document_type에 baseball_rule, common_play, latest_kbo_rule 추가 가능 여부
retriever에서 stadium_id 필터 없이 document_type/knowledge_type 기반 검색 가능하도록 확장
metadata JSONB에 knowledge_type, topic_id, season_year, is_latest, source_pages 저장
```

임베딩 모델:

```text
text-embedding-3-small
1536 dimensions
```

Upsert 전략:

```text
document_id/topic_id 기준 idempotent upsert
content_hash 변경 시 embedding 재생성
is_latest=true chunk를 기본 검색 대상으로 우선
과거 연도 chunk는 변경점 질의 또는 fallback용으로 유지
```

## 10. 평가 계획

초기 라우팅/검색 평가 질문:

```text
보크가 뭐야?
인필드 플라이가 왜 선언돼?
포스아웃이랑 태그아웃 차이가 뭐야?
페어랑 파울은 어떻게 구분해?
볼넷이 뭐야?
삼진이면 무조건 아웃이야?
도루랑 견제는 뭐가 달라?
희생플라이가 뭐야?
폭투랑 포일 차이가 뭐야?
비디오 판독은 아무거나 신청할 수 있어?
ABS가 뭐야?
피치클락 위반하면 어떻게 돼?
우천 노게임은 뭐야?
서스펜디드 게임이 뭐야?
경기 취소는 누가 결정해?
```

초기 완료 기준:

```text
6개 PDF 기본 텍스트 추출 성공
2026 최신본 기준 MVP topic 20개 이상 curated chunk 생성
각 chunk에 source document/page metadata 포함
OpenAI embedding 입력 JSONL 생성
대표 질문 15개 중 12개 이상 적절한 topic chunk top-3 검색
Tool routing에서 야구 규칙/플레이 질문이 search_baseball_knowledge로 분류
```

## 11. 다음 작업

1. PDF extraction script 작성
2. 2026 PDF 기준 page JSONL 추출
3. topic별 source page slice 검수
4. `data/baseball_knowledge/sources.json` 작성
5. curated normalized JSON 작성
6. chunk generation script 작성
7. embedding/upsert script 작성
8. retriever/handler/schema 구현
9. routing schema/tool card/prompt 연결
10. 평가 케이스 작성
