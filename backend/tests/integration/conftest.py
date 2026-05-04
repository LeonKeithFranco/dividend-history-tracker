import asyncio
from collections.abc import AsyncIterator, Coroutine, Iterator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app
from database.db import Base
from database.db.session import get_db
from scraper import DividendEvent, DividendHistory, DividendMetrics, StockInfo


def _run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine synchronously in a new event loop.

    Used to execute async setup and teardown operations (e.g. creating tables,
    disposing engines) from synchronous pytest fixtures.

    Args:
        coro: The coroutine to execute.

    Returns:
        Any: The return value of the coroutine.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _create_tables(engine: AsyncEngine) -> None:
    """Create all ORM tables in the given engine's database.

    Args:
        engine: The async SQLAlchemy engine to create tables against.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Provide a FastAPI TestClient backed by an in-memory SQLite database.

    Creates a fresh in-memory database for each test, overrides the get_db
    dependency to use it, and cleans up the engine after the test completes.
    Uses StaticPool so the same in-memory database is shared across the
    synchronous TestClient and the async application code.

    Yields:
        TestClient: A configured test client for the FastAPI application.
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestAsyncSessionFactory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    _run_async(_create_tables(test_engine))

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with TestAsyncSessionFactory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    _run_async(test_engine.dispose())


@pytest.fixture
def mock_stock_info() -> StockInfo:
    """Canned StockInfo matching AAPL for use in mocked scraper responses."""
    return StockInfo(
        company_name="Apple Inc.",
        ticker_symbol="AAPL",
        exchange="NASDAQ",
    )


@pytest.fixture
def mock_dividend_metrics() -> DividendMetrics:
    """Canned DividendMetrics for use in mocked scraper responses."""
    return DividendMetrics(
        yield_=0.44,
        payout_ratio=16.2,
        frequency="Quarterly",
        annual_dividend=Decimal("1.00"),
        next_ex_dividend_date=date(2026, 8, 11),
        next_payout_date=date(2026, 8, 14),
    )


@pytest.fixture
def mock_dividend_history() -> DividendHistory:
    """Canned DividendHistory with two events for use in mocked scraper responses."""
    return DividendHistory(
        dividend_events=[
            DividendEvent(
                ex_dividend_date=date(2026, 5, 12),
                payout_date=date(2026, 5, 15),
                cash_amount=Decimal("0.27"),
                pct_change=4.1,
            ),
            DividendEvent(
                ex_dividend_date=date(2026, 2, 9),
                payout_date=date(2026, 2, 12),
                cash_amount=Decimal("0.26"),
                pct_change=None,
            ),
        ]
    )


@pytest.fixture
def mock_scraper_response(
    mock_stock_info: StockInfo,
    mock_dividend_metrics: DividendMetrics,
    mock_dividend_history: DividendHistory,
) -> tuple[StockInfo, DividendMetrics, DividendHistory]:
    """Composite fixture bundling stock info, metrics, and history into a tuple.

    Matches the return type of get_dividend_info so it can be used directly
    as a mock return value.
    """
    return (mock_stock_info, mock_dividend_metrics, mock_dividend_history)
