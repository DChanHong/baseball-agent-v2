from __future__ import annotations

# 정규화된 구장 가이드 JSON 문서를 RAG chunk JSONL 입력으로 변환한다.
# 생성된 chunk에는 source URL과 embedding text가 포함되며 vector 값은 포함하지 않는다.

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate stadium guide RAG chunk JSONL from normalized documents."
    )
    parser.add_argument(
        "--stadium-id",
        default="SAJIK",
        help="Stadium ID to export. Defaults to SAJIK.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project root directory. Defaults to the repository root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path. Defaults to data/stadium_guide/embedded_input/stadium_guide_chunks.jsonl.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def build_source_url_index(sources_path: Path) -> dict[str, str]:
    registry = load_json(sources_path)
    sources = registry.get("sources", [])
    return {
        source["source_id"]: source["url"]
        for source in sources
        if source.get("source_id") and source.get("url")
    }


def build_embedding_text(document: dict[str, Any]) -> str:
    team_id = document.get("team_id") or "공통"
    return "\n".join(
        [
            f"제목: {document['title']}",
            f"문서유형: {document['document_type']}",
            f"구장: {document['stadium_id']}",
            f"팀: {team_id}",
            "본문:",
            document["content"],
        ]
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chunk(
    document: dict[str, Any],
    source_file: Path,
    project_root: Path,
    source_url_index: dict[str, str],
) -> dict[str, Any]:
    source_ids = document.get("sources", [])
    source_urls = [
        source_url_index[source_id]
        for source_id in source_ids
        if source_id in source_url_index
    ]
    embedding_text = build_embedding_text(document)
    content_hash = sha256_text(embedding_text)
    document_id = document["document_id"]

    return {
        "schema_version": "1.0.0",
        "chunk_id": f"{document_id}_chunk_000",
        "document_id": document_id,
        "chunk_index": 0,
        "document_type": document["document_type"],
        "stadium_id": document["stadium_id"],
        "team_id": document.get("team_id"),
        "title": document["title"],
        "as_of": document["as_of"],
        "trust_level": document["trust_level"],
        "review_status": document["review_status"],
        "source_ids": source_ids,
        "source_urls": source_urls,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_dimensions": DEFAULT_EMBEDDING_DIMENSIONS,
        "embedding_text": embedding_text,
        "content": document["content"],
        "content_hash": content_hash,
        "metadata": {
            **document.get("metadata", {}),
            "language": "ko",
            "source_file": str(source_file.relative_to(project_root)),
        },
    }


def iter_normalized_documents(
    normalized_dir: Path,
) -> list[tuple[Path, dict[str, Any]]]:
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(normalized_dir.glob("*.json")):
        documents.append((path, load_json(path)))
    return documents


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    stadium_id = args.stadium_id.upper()
    normalized_dir = project_root / "data" / "stadium_guide" / "normalized" / stadium_id
    sources_path = project_root / "data" / "stadium_guide" / "sources.json"
    output_path = args.output or (
        project_root
        / "data"
        / "stadium_guide"
        / "embedded_input"
        / "stadium_guide_chunks.jsonl"
    )

    if not normalized_dir.exists():
        raise FileNotFoundError(f"Normalized directory does not exist: {normalized_dir}")

    source_url_index = build_source_url_index(sources_path)
    documents = iter_normalized_documents(normalized_dir)
    chunks = [
        build_chunk(document, source_file, project_root, source_url_index)
        for source_file, document in documents
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True))
            file.write("\n")

    print(f"Wrote {len(chunks)} chunks to {output_path}")


if __name__ == "__main__":
    main()
