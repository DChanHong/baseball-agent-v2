from enum import StrEnum


class KboGameStatus(StrEnum):
    """KBO 경기 상태입니다."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"
    UNKNOWN = "unknown"
