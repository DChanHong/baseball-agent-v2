from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from .schemas import ParsedSource


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_raw_snapshot(raw_root: Path, parsed: ParsedSource) -> ParsedSource:
    scope = parsed.collected.source.stadium_ids[0] if parsed.collected.source.stadium_ids else "COMMON"
    folder = raw_root / parsed.collected.collected_at.date().isoformat() / scope
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{parsed.collected.source.source_id}_{parsed.raw_hash[:12]}.html"
    if not path.exists():
        path.write_text(parsed.collected.body, encoding="utf-8")
    return replace(parsed, raw_file_path=path)

