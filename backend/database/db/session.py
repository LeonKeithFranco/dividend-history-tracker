from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings

_engine = create_async_engine(
    get_settings().db_url,
    echo=get_settings().app_debug,
)

AsyncSessionFactory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session for the duration of a request.

    Used as a FastAPI dependency. The session is automatically closed when the
    request completes.

    Yields:
        AsyncSession: A scoped async database session.
    """
    async with AsyncSessionFactory() as session:
        yield session
