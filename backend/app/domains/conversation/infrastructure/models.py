from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# auth.users는 Supabase Auth가 관리하므로 애플리케이션 ORM Model을 만들지 않습니다.
# 다만 user_id ForeignKey를 SQLAlchemy가 해석할 수 있도록 최소 메타데이터만 등록합니다.
AUTH_USERS_TABLE = Table(
    "users",
    Base.metadata,
    Column(
        "id",
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    ),
    schema="auth",
)


class ChatConversationModel(Base):
    """chat_conversations 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "chat_conversations"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    # 대화방 기본키입니다. UUID 생성은 PostgreSQL이 담당합니다.
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # 로그인 도입 후 auth.users.id와 연결할 사용자 식별자입니다.
    user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 로그인 전 브라우저 사용자를 식별하는 임시 UUID입니다.
    guest_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
    )

    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'baseball_general'"),
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # metadata는 SQLAlchemy가 내부적으로 사용하는 예약 이름입니다.
    # Python에서는 extra_metadata로 접근하고 실제 컬럼은 metadata를 사용합니다.
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # updated_at 자동 변경은 migration에서 만든 DB trigger가 담당합니다.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL이면 정상 대화, 값이 있으면 소프트 삭제된 대화입니다.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ChatMessageModel(Base):
    """chat_messages 테이블과 연결되는 SQLAlchemy ORM 모델입니다."""

    __tablename__ = "chat_messages"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "public"}

    # 메시지 기본키입니다.
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # 메시지가 소속된 대화방입니다.
    # 대화방이 물리 삭제되면 메시지도 함께 삭제됩니다.
    conversation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "public.chat_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # 로그인 도입 후 메시지를 작성한 사용자와 연결됩니다.
    user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # user, assistant, system, tool 중 하나입니다.
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # 실제 메시지 본문입니다.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # text, markdown, json, image, file 중 하나입니다.
    content_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'markdown'"),
    )

    # 한 대화방 안에서 메시지 순서를 나타냅니다.
    sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # pending, streaming, completed, failed, cancelled 중 하나입니다.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'completed'"),
    )

    # 재생성 또는 분기의 기준이 된 메시지입니다.
    parent_message_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "public.chat_messages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # assistant 메시지를 생성한 AI 모델 이름입니다.
    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    completion_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # AI 응답 생성에 걸린 시간이며 단위는 밀리초입니다.
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # 메시지 처리 실패 시 내부 오류 코드를 저장합니다.
    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # 도구 호출, 인용, 검색 결과 등의 부가 정보입니다.
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    # updated_at 자동 변경은 DB trigger가 담당합니다.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
