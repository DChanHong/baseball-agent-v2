# 비동기 제너레이터 함수의 반환 타입을 표현할 때 사용합니다.
# get_db_session()이 AsyncSession을 하나씩 제공한다는 것을 나타냅니다.
from collections.abc import AsyncIterator

# SQLAlchemy의 비동기 데이터베이스 기능입니다.
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 모든 SQLAlchemy ORM 모델이 상속할 기본 클래스를 만드는 도구입니다.
from sqlalchemy.orm import DeclarativeBase

# .env에서 읽은 애플리케이션 설정을 가져옵니다.
from app.core.config import get_settings


class Base(DeclarativeBase):
    """
    모든 SQLAlchemy ORM 모델의 공통 부모 클래스입니다.

    이후 ChatConversation, ChatMessage 등의 모델은
    이 클래스를 상속하여 데이터베이스 테이블과 연결됩니다.
    """


# get_settings()는 캐시된 Settings 객체를 반환합니다.
# 여기에는 DATABASE_URL, APP_DEBUG 등의 환경변수 값이 들어 있습니다.
settings = get_settings()


# 애플리케이션 전체에서 사용할 비동기 DB 엔진입니다.
engine = create_async_engine(
    # 예: postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
    settings.database_url,
    # True이면 실행되는 SQL을 터미널에 출력합니다.
    # 로컬 개발에서는 유용하지만 운영 환경에서는 보통 False로 설정합니다.
    echo=settings.app_debug,
    # 커넥션 풀에서 연결을 꺼낼 때 연결이 유효한지 먼저 검사합니다.
    # 오래되어 끊어진 연결을 재사용하면서 발생하는 오류를 줄여줍니다.
    pool_pre_ping=True,
    # Supabase transaction pooler는 prepared statement를 지원하지 않으므로
    # asyncpg의 statement cache를 비활성화합니다.
    connect_args={"statement_cache_size": 0},
)


# 요청마다 AsyncSession을 생성할 수 있는 세션 팩토리입니다.
async_session_factory = async_sessionmaker(
    # 위에서 만든 비동기 DB 엔진을 사용합니다.
    bind=engine,
    # 팩토리가 생성할 세션의 클래스입니다.
    class_=AsyncSession,
    # commit 이후에도 ORM 객체의 속성값을 유지합니다.
    # False로 설정하면 응답 객체를 만들 때 불필요한 재조회가 줄어듭니다.
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI 엔드포인트에 DB 세션을 제공하는 의존성 함수입니다.

    요청이 시작되면 세션을 생성하고, 요청 처리가 끝나면 세션을 닫습니다.
    처리 중 예외가 발생하면 현재 트랜잭션을 rollback한 뒤
    동일한 예외를 다시 발생시킵니다.
    """

    # async with 블록이 끝나면 세션이 자동으로 닫힙니다.
    async with async_session_factory() as session:
        try:
            # yield를 통해 FastAPI 엔드포인트에 세션을 전달합니다.
            yield session
        except Exception:
            # 처리 중 오류가 발생했다면 미완료 변경 사항을 되돌립니다.
            await session.rollback()

            # FastAPI의 예외 처리기가 처리할 수 있도록 다시 발생시킵니다.
            raise
