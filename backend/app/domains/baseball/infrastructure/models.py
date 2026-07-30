from datetime import date, datetime, time
from typing import ClassVar
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KboTeamModel(Base):
    """kbo_teams 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "kbo_teams"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_ko: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
    )
    home_stadium_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("public.kbo_stadiums.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    office_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticket_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticket_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class KboStadiumModel(Base):
    """kbo_stadiums 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "kbo_stadiums"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_ko: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
    )
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_team_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("public.kbo_teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    is_dome: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class KboGameModel(Base):
    """kbo_games 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "kbo_games"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_game_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_game_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    away_team_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("public.kbo_teams.id"),
        nullable=False,
    )
    home_team_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("public.kbo_teams.id"),
        nullable=False,
    )
    stadium_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("public.kbo_stadiums.id"),
        nullable=False,
    )
    away_team_name: Mapped[str] = mapped_column(Text, nullable=False)
    home_team_name: Mapped[str] = mapped_column(Text, nullable=False)
    stadium_name: Mapped[str] = mapped_column(Text, nullable=False)
    game_status: Mapped[str] = mapped_column(String(20), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'KBO'"),
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class KboGameStatusHistoryModel(Base):
    """kbo_game_status_history 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "kbo_game_status_history"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    game_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("public.kbo_games.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
