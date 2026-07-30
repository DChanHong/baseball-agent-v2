# 작업 로그 템플릿

> 이 파일은 블로그 초안이 아니라, 프로젝트를 진행하며 글감과 의사결정 히스토리를 남기기 위한 작업 기록 템플릿이다.
> 실제 글을 작성할 때는 여러 작업 로그를 묶어서 하나의 스토리형 포스트로 재구성한다.

## 기본 정보

```text
날짜:
작업 범위:
관련 브랜치/커밋:
관련 파일:
```

## 오늘의 목표

```text
예:
SAJIK 구장 가이드 normalized JSON 5개를 chunk로 만들고,
Supabase pgvector에 최소 임베딩 실험을 해본다.
```

## 왜 이 작업을 하는가

```text
예:
경기 일정 조회는 정형 DB로 처리할 수 있지만,
구장별 입장/반입/교통/좌석 안내는 출처와 형식이 제각각이라 RAG가 필요하다.
이번 작업은 야구 Agent가 구장 지식을 검색해서 답변하기 위한 첫 실험이다.
```

## 작업 전 상태

```text
예:
- SAJIK normalized 문서 5개가 있다.
- 아직 embedding/chunk 테이블은 없다.
- review_status는 needs_review 상태다.
- Supabase pgvector에는 아직 구장 가이드 문서가 없다.
```

## 오늘 결정한 것

```text
예:
- 첫 실험은 SAJIK만 대상으로 한다.
- 문서 1개를 chunk 1개로 유지한다.
- review_status가 needs_review여도 실험용으로 임베딩한다.
- 검색 시 stadium_id filter를 반드시 건다.
```

## 구현하거나 만든 것

```text
예:
- rag_documents / rag_chunks migration 추가
- SAJIK chunk JSONL 생성 스크립트 추가
- OpenAI embedding 생성 후 Supabase upsert 스크립트 추가
- 검색 테스트용 SQL 또는 Python script 추가
```

## 확인한 결과

```text
예:
- "사직구장 지하철" 질문에서 stadium_transport_guide chunk가 검색됐다.
- "사직구장 반입" 질문에서 stadium_bag_policy chunk가 검색됐다.
- top_k=3 기준으로 document_type이 섞이는지 확인했다.
```

## 막힌 점

```text
예:
- source_id를 source_url로 매핑하는 과정이 아직 느슨하다.
- review_status 기준이 없어 approved 검색 정책을 적용하지 못했다.
- ticketing 문서는 가격/할인 정보가 많아 chunk 분할 기준이 필요할 수 있다.
```

## 다음 작업

```text
예:
- review_status 승인 기준 문서화
- SAJIK 검색 테스트 케이스 저장
- JAMSIL 수집 전에 LG/DOOSAN 홈팀별 문서 분리 기준 정리
```

## 블로그에 살릴 포인트

```text
예:
- 처음에는 구장 정보를 테이블에 넣으려고 했지만, 구장마다 출처와 형식이 달라 RAG로 분리했다.
- 전체 구장을 한 번에 하지 않고 SAJIK 하나만 vertical slice로 검증했다.
- AI Agent에서 중요한 것은 모델 연결보다, 믿을 수 있는 지식과 출처를 어떻게 준비하느냐였다.
```

## 블로그 초안 문장

```text
예:
야구 Agent를 만들면서 가장 먼저 부딪힌 문제는 "정보를 어디에 넣을 것인가"였다.
경기 일정처럼 날짜와 팀이 명확한 데이터는 테이블에 잘 맞았다.
하지만 "사직구장 처음 가는데 뭐 챙겨야 해?"라는 질문은 달랐다.
이 질문에는 반입 정책, 교통, 좌석, 티켓, 초행자 준비물이 섞여 있고,
각 정보의 출처도 구단 공식 사이트, KBO 공통 안내, 시설 안내로 나뉘었다.
```

## 커밋 메모

```text
커밋 전 확인:
- git status --short
- git diff --check
- 필요한 테스트/스크립트 실행 여부

커밋 메시지 후보:
```

