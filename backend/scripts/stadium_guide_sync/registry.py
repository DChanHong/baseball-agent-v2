from __future__ import annotations

import json
from pathlib import Path

from .schemas import SourceDefinition, SourceRegistry


def load_registry(path: Path) -> SourceRegistry:
    return SourceRegistry.model_validate_json(path.read_text(encoding="utf-8"))


def select_sources(
    registry: SourceRegistry,
    *,
    stadium_id: str | None = None,
    source_id: str | None = None,
    document_type: str | None = None,
    include_all: bool = False,
) -> list[SourceDefinition]:
    selected: list[SourceDefinition] = []
    for source in registry.sources:
        if not source.enabled:
            continue
        if source_id and source.source_id != source_id:
            continue
        if document_type and document_type not in source.document_types:
            continue
        if not include_all and not source_id:
            if not stadium_id:
                continue
            if source.stadium_ids and stadium_id not in source.stadium_ids:
                continue
        selected.append(source)
    return selected


def registry_contract(path: Path) -> dict[str, object]:
    """Return the normalized registry, useful for validation and diagnostics."""
    return json.loads(load_registry(path).model_dump_json())
