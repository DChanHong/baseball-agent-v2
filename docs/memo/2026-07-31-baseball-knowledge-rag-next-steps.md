# Baseball Knowledge RAG Next Steps

> 작성일: 2026-07-31  
> 목적: 다음 세션에서 `search_baseball_knowledge` RAG/Tool 작업을 바로 이어가기 위한 메모  
> 현재 기준 커밋: `73aeb94 feat: add baseball knowledge embedding pipeline`  
> 중요: OpenAI embedding 및 DB upsert는 아직 실행하지 않았다.

## 1. 현재까지 완료된 작업

야구 지식 RAG용 데이터/임베딩 파이프라인의 1차 구현을 완료했다.

추가된 주요 파일:

```text
backend/scripts/baseball_knowledge/
  extract_pdf_pages.py
  generate_chunks.py
  embed_chunks.py

data/baseball_knowledge/
  .gitignore
  README.md
  sources.json

docs/embedding/
  baseball-knowledge-rag-plan-v1-1.md
  stadium-guide-rag-status-v1-1.md
```

의존성:

```text
pdfplumber>=0.11.10
```

`backend/pyproject.toml`, `backend/uv.lock`에 반영되어 있다.

## 2. 원본 PDF 위치

PDF 원본은 git에 포함하지 않는다. 필요할 때 사용자가 로컬 경로를 제공한다.

현재 사용한 로컬 PDF 경로:

```text
/Users/hong/Desktop/야구지식-RAG용
```

확인된 PDF:

```text
2024_야구규칙.pdf
2025_야구규칙.pdf
2026_야구규칙.pdf
2024_리그규정.pdf
2025_리그규정.pdf
2026_리그규정.pdf
```

## 3. 현재 데이터 소스 범위

MVP source:

```text
공식야구규칙 PDF: 2024, 2025, 2026
KBO 리그 규정 PDF: 2024, 2025, 2026
KBO 주요 규정/규칙 웹페이지: 2026 보조 출처
```

현재 `data/baseball_knowledge/sources.json`에는 위 source registry가 들어 있다.

현재 제외:

```text
야구장 관람 가이드북
KBO 연감
레코드북
기록대백과
기록/스탯 심화
선수/팀 히스토리
구장별 관람 정보
```

## 4. 구현된 스크립트

### 4.1 PDF page extraction

```text
backend/scripts/baseball_knowledge/extract_pdf_pages.py
```

역할:

```text
외부 PDF 디렉터리 입력
pdfplumber 기반 page-level text 추출
data/baseball_knowledge/raw/extracted_pdf 아래 JSONL 생성
data/baseball_knowledge/sources.json 생성/갱신
manifest.json 생성
```

기본 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/extract_pdf_pages.py --pdf-dir "/Users/hong/Desktop/야구지식-RAG용" --strict
```

주의:

```text
data/baseball_knowledge/raw/는 .gitignore 대상이다.
추출 산출물은 재생성 가능하므로 commit하지 않는다.
```

### 4.2 Chunk generation

```text
backend/scripts/baseball_knowledge/generate_chunks.py
```

역할:

```text
추출된 page-level JSONL을 topic 기반 RAG chunk JSONL로 변환
긴 topic은 자동으로 chunk_000, chunk_001처럼 분할
data/baseball_knowledge/embedded_input/baseball_knowledge_chunks.jsonl 생성
```

기본 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
```

현재 topic 결과:

```text
27 chunks
최대 embedding_text 길이 약 6.5k chars
```

주의:

```text
data/baseball_knowledge/embedded_input/는 현재 .gitignore 대상이다.
현재 chunk는 PDF 원문 page slice 기반 source-grounded chunk다.
초보자용 curated 설명문은 후속 단계에서 보강한다.
```

### 4.3 Embedding/upsert

```text
backend/scripts/baseball_knowledge/embed_chunks.py
```

역할:

```text
baseball_knowledge_chunks.jsonl 로드
OpenAI embeddings API 호출
public.rag_documents, public.rag_chunks에 upsert
```

dry-run 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
```

실제 embedding/upsert 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/embed_chunks.py
```

중요:

```text
아직 실제 embedding/upsert는 실행하지 않았다.
다음 세션에서 사용자가 명시적으로 원할 때만 실행한다.
OPENAI_API_KEY, DATABASE_URL 필요.
```

## 5. 검증 완료 내역

실행/검증은 임시 경로(`/tmp`)에서 수행했다.

검증 결과:

```text
pdfplumber로 6개 PDF 추출 성공
chunk 생성 성공: 27 chunks
embed_chunks.py --dry-run 통과
ruff check 통과
py_compile 통과
git worktree clean 상태에서 커밋 완료
```

실제 embedding API 호출:

```text
미실행
```

DB upsert:

```text
미실행
```

## 6. 다음 세션 시작 명령

```bash
cd /Users/hong/Desktop/baseball-agent-v2
git status --short
git log --oneline -5
sed -n '1,260p' docs/memo/2026-07-31-baseball-knowledge-rag-next-steps.md
```

## 7. 다음 작업 추천 순서

1. PDF 원본 경로가 그대로 있는지 확인

```bash
ls -1 "/Users/hong/Desktop/야구지식-RAG용"
```

2. PDF page extraction 재생성

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/extract_pdf_pages.py --pdf-dir "/Users/hong/Desktop/야구지식-RAG용" --strict
```

3. chunk JSONL 재생성

```bash
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
```

4. dry-run 확인

```bash
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
```

5. 사용자가 승인하면 실제 embedding/upsert 실행

```bash
uv run python scripts/baseball_knowledge/embed_chunks.py
```

6. DB에 들어간 chunk 수 확인

```sql
select document_type, count(*)
from public.rag_chunks
where metadata->>'topic_id' is not null
group by document_type
order by document_type;
```

7. 이후 `search_baseball_knowledge` Tool 구현

```text
backend/app/domains/baseball/tool/search_baseball_knowledge/
  __init__.py
  schemas.py
  handler.py
  retriever.py
```

연결 파일:

```text
backend/app/agent/routing_schemas.py
backend/app/agent/tool_cards.py
backend/app/agent/prompts.py
backend/app/agent/tool_executor.py
backend/app/api/dependencies.py
```

## 8. 현재 한계와 후속 보강

현재 chunk는 PDF 원문 발췌 중심이다.

후속 보강 후보:

```text
초보자용 curated 설명문 생성
KBO 주요 규정/규칙 웹페이지 HTML 수집 및 normalized 문서 추가
topic별 검색 평가 케이스 15~20개 작성
search_baseball_knowledge retriever 구현
Tool routing에서 야구 규칙/플레이 질문 연결
source page citation 표시 정책 정리
```

현재 긴 topic은 자동 분할되지만, 의미 단위 section split은 아직 아니다. 검색 품질 평가 후 필요하면 조항/section 단위 분할로 개선한다.
