# Baseball Knowledge Data

`search_baseball_knowledge` RAG 후보 데이터와 검색 평가 데이터를 보관한다.

PDF 원본은 용량과 재배포 이슈 때문에 repo에 포함하지 않는다. 필요할 때 사용자가 로컬 PDF 경로를 제공하고, `pdfplumber` 기반 page-level extraction과 chunk JSONL 산출물을 재생성한다.

## 구조

```text
data/baseball_knowledge/
├── README.md
├── sources.json
├── raw/
│   ├── extracted_pdf/
│   └── web/
├── normalized/
├── embedded_input/
│   └── baseball_knowledge_chunks.jsonl
└── evaluation/
    ├── cases/
    └── runs/
```

## 기본 명령

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run python scripts/baseball_knowledge/extract_pdf_pages.py --pdf-dir "/Users/hong/Desktop/야구지식-RAG용" --strict
uv run python scripts/baseball_knowledge/generate_chunks.py --strict
uv run python scripts/baseball_knowledge/embed_chunks.py --dry-run
uv run python scripts/baseball_knowledge/embed_chunks.py
```

## Git 관리 원칙

```text
raw/는 PDF 원문에서 재생성되는 page-level text라 commit하지 않는다.
embedded_input/은 현재 source-grounded chunk 생성물이라 commit하지 않는다.
sources.json과 script만 commit한다.
curated chunk를 사람이 검수한 fixture로 운영하기로 결정하면 embedded_input ignore 정책을 변경한다.
```
