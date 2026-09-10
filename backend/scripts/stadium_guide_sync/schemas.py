from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

SUPPORTED_DOCUMENT_TYPES = {
    "stadium_bag_policy",
    "stadium_facility_guide",
    "stadium_seat_guide",
    "stadium_ticketing_guide",
    "stadium_transport_guide",
    "stadium_food_guide",
    "stadium_entry_guide",
    "stadium_accessibility_guide",
}
LEGACY_DOCUMENT_TYPES = {"stadium_first_visit_tip"}


class CollectorType(StrEnum):
    HTTP = "http"
    BROWSER = "browser"


class SourceDefinition(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    source_type: str
    stadium_ids: list[str] = Field(default_factory=list)
    team_ids: list[str] = Field(default_factory=list)
    document_types: list[str]
    collector_type: CollectorType = CollectorType.HTTP
    parser_name: str = "visible_text"
    refresh_policy: str
    trust_level: str
    enabled: bool = True
    notes: str = ""
    local_raw_file: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_singular_ids(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "stadium_ids" not in normalized:
            stadium_id = normalized.pop("stadium_id", None)
            normalized["stadium_ids"] = [stadium_id] if stadium_id else []
        if "team_ids" not in normalized:
            team_id = normalized.pop("team_id", None)
            normalized["team_ids"] = [team_id] if team_id else []
        return normalized

    @model_validator(mode="after")
    def validate_document_types(self) -> SourceDefinition:
        unknown = set(self.document_types) - SUPPORTED_DOCUMENT_TYPES - LEGACY_DOCUMENT_TYPES
        if unknown:
            raise ValueError(f"unsupported document_types: {sorted(unknown)}")
        return self


class SourceRegistry(BaseModel):
    schema_version: str
    as_of: date
    description: str
    sources: list[SourceDefinition]

    @model_validator(mode="after")
    def validate_unique_source_ids(self) -> SourceRegistry:
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("source_id must be unique")
        return self


@dataclass(frozen=True, slots=True)
class CollectedSource:
    source: SourceDefinition
    collected_at: datetime
    body: str
    status_code: int
    collector_type: str


@dataclass(frozen=True, slots=True)
class ParsedSource:
    collected: CollectedSource
    text: str
    raw_hash: str
    text_hash: str
    raw_file_path: Path | None = None


class CandidateDraft(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=40)
    as_of: date
    topic_summary: str = Field(min_length=1)
    search_keywords: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class ActiveDocument(BaseModel):
    document_id: str
    logical_document_id: str
    revision_number: int
    content_hash: str
    title: str
    content: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ChangeOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    UNCHANGED = "UNCHANGED"
    DELETE_CANDIDATE = "DELETE_CANDIDATE"
    RE_EMBED = "RE_EMBED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
