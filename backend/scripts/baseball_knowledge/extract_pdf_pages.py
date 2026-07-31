from __future__ import annotations

# KBO 공식 PDF 원본을 page-level JSONL로 추출한다.
# PDF 원본은 repo 밖 경로를 입력으로 받고, 추출 산출물만 data/baseball_knowledge에 저장한다.
import argparse
import contextlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PdfSource:
    filename: str
    source_id: str
    document_type: str
    title: str
    season_year: int
    output_slug: str


PDF_SOURCES = [
    PdfSource(
        filename="2024_야구규칙.pdf",
        source_id="kbo_2024_official_baseball_rules",
        document_type="official_baseball_rules",
        title="2024 공식야구규칙",
        season_year=2024,
        output_slug="official_baseball_rules",
    ),
    PdfSource(
        filename="2025_야구규칙.pdf",
        source_id="kbo_2025_official_baseball_rules",
        document_type="official_baseball_rules",
        title="2025 공식야구규칙",
        season_year=2025,
        output_slug="official_baseball_rules",
    ),
    PdfSource(
        filename="2026_야구규칙.pdf",
        source_id="kbo_2026_official_baseball_rules",
        document_type="official_baseball_rules",
        title="2026 공식야구규칙",
        season_year=2026,
        output_slug="official_baseball_rules",
    ),
    PdfSource(
        filename="2024_리그규정.pdf",
        source_id="kbo_2024_league_rules",
        document_type="league_rules",
        title="2024 KBO 리그 규정",
        season_year=2024,
        output_slug="league_rules",
    ),
    PdfSource(
        filename="2025_리그규정.pdf",
        source_id="kbo_2025_league_rules",
        document_type="league_rules",
        title="2025 KBO 리그 규정",
        season_year=2025,
        output_slug="league_rules",
    ),
    PdfSource(
        filename="2026_리그규정.pdf",
        source_id="kbo_2026_league_rules",
        document_type="league_rules",
        title="2026 KBO 리그 규정",
        season_year=2026,
        output_slug="league_rules",
    ),
]

SOURCE_URLS = {
    "kbo_publications_category": "https://www.koreabaseball.com/Kbo/Board/Ebook/EbookCategory.aspx",
}
PDF_EXTRACTOR = "pdfplumber"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract KBO baseball knowledge PDF pages into JSONL files."
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory containing downloaded KBO PDF files.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Project root directory. Defaults to the repository root.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Output root. Defaults to data/baseball_knowledge/raw/extracted_pdf.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when any expected PDF is missing.",
    )
    return parser.parse_args()


def import_pdfplumber() -> Any:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pdfplumber is required to extract PDF text. Install backend dependencies "
            "or run `uv add pdfplumber` from the backend directory."
        ) from exc

    return pdfplumber


def normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_source(pdf_dir: Path, output_root: Path, source: PdfSource) -> dict[str, Any]:
    pdfplumber = import_pdfplumber()
    pdf_path = pdf_dir / source.filename
    if not pdf_path.exists():
        return {
            "source_id": source.source_id,
            "filename": source.filename,
            "status": "missing",
        }

    with contextlib.redirect_stderr(io.StringIO()), pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        output_path = (
            output_root
            / str(source.season_year)
            / f"{source.output_slug}_pages.jsonl"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        non_empty_pages = 0
        with output_path.open("w", encoding="utf-8") as file:
            for page_index, page in enumerate(pdf.pages):
                raw_text = page.extract_text(layout=False) or ""
                text = normalize_text(raw_text)
                if text:
                    non_empty_pages += 1

                record = {
                    "schema_version": "1.0.0",
                    "source_id": source.source_id,
                    "source_file": source.filename,
                    "source_url": SOURCE_URLS["kbo_publications_category"],
                    "document_type": source.document_type,
                    "document_title": source.title,
                    "season_year": source.season_year,
                    "page_number": page_index + 1,
                    "extractor": PDF_EXTRACTOR,
                    "text": text,
                    "char_count": len(text),
                    "extraction_status": "ok" if text else "empty_text",
                }
                file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                file.write("\n")

    return {
        "source_id": source.source_id,
        "filename": source.filename,
        "status": "extracted",
        "output_path": str(output_path),
        "page_count": page_count,
        "non_empty_pages": non_empty_pages,
        "extractor": PDF_EXTRACTOR,
    }


def write_sources_registry(project_root: Path) -> Path:
    output_path = project_root / "data" / "baseball_knowledge" / "sources.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sources = [
        {
            "source_id": source.source_id,
            "title": source.title,
            "document_type": source.document_type,
            "season_year": source.season_year,
            "source_kind": "pdf",
            "extractor": PDF_EXTRACTOR,
            "source_url": SOURCE_URLS["kbo_publications_category"],
            "local_filename": source.filename,
            "repo_tracked": False,
        }
        for source in PDF_SOURCES
    ]
    sources.append(
        {
            "source_id": "kbo_2026_game_manage_rules_page",
            "title": "2026 주요 규정 및 규칙",
            "document_type": "latest_kbo_rules_web",
            "season_year": 2026,
            "source_kind": "web_page",
            "source_url": "https://www.koreabaseball.com/Kbo/League/GameManage2026.aspx",
            "repo_tracked": False,
        }
    )
    payload = {
        "schema_version": "1.0.0",
        "sources": sources,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    pdf_dir = args.pdf_dir.expanduser().resolve()
    output_root = args.output_root or (
        project_root / "data" / "baseball_knowledge" / "raw" / "extracted_pdf"
    )
    output_root = output_root.resolve()

    results = [extract_source(pdf_dir, output_root, source) for source in PDF_SOURCES]
    missing = [result["filename"] for result in results if result["status"] == "missing"]
    if args.strict and missing:
        raise FileNotFoundError(f"Missing expected PDFs: {missing}")

    manifest_path = output_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "pdf_dir": str(pdf_dir), "results": results},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    sources_path = write_sources_registry(project_root)

    extracted_count = sum(1 for result in results if result["status"] == "extracted")
    print(f"Extracted {extracted_count} PDF files into {output_root}")
    print(f"Wrote manifest to {manifest_path}")
    print(f"Wrote source registry to {sources_path}")
    if missing:
        print(f"Missing PDFs: {', '.join(missing)}")


if __name__ == "__main__":
    main()
