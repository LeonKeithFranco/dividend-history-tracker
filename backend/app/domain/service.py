from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import BackgroundTasks, Depends

from app.domain.repository import StockRepoDependency, StockRepository
from app.domain.schemas import StockDividendHistoryResponse
from database.db import AsyncSessionFactory
from database.models import Stock
from scraper import async_get_dividend_info
from scraper.scraper import async_get_just_dividend_history


async def _do_refresh(ticker: str, stock_repo: StockRepository) -> None:
    """Re-scrape dividend events for a ticker and persist any new ones.

    Fetches the latest dividend history from the data source, compares it
    against the most recent event already stored, and inserts only the events
    that are newer. Updates the stock's date_refreshed timestamp.

    Args:
        ticker: The ticker symbol to refresh.
        stock_repo: The repository instance to use for database access.
    """
    new_dividend_history = await async_get_just_dividend_history(ticker)

    stock = cast(Stock, await stock_repo.get_stock(ticker))

    latest_ex_dividend_date = (
        stock.events[-1].ex_dividend_date if stock.events else datetime.min
    )

    new_dividend_events = [
        event
        for event in new_dividend_history.dividend_events
        if event.ex_dividend_date > latest_ex_dividend_date
    ]

    stock.date_refreshed = datetime.now(UTC)
    await stock_repo.insert_new_dividend_events(stock, new_dividend_events)


async def _update_dividend_history(ticker: str) -> None:
    """Background-task entry point for refreshing a ticker's dividend events.

    Creates its own database session so it can run independently of the
    request that scheduled it. Intended to be passed to FastAPI's
    BackgroundTasks.

    Args:
        ticker: The ticker symbol to refresh.
    """
    async with AsyncSessionFactory() as db:
        stock_repo = StockRepository(db)
        await _do_refresh(ticker, stock_repo)
        await stock_repo.commit()


class DividendHistoryService:
    """Service layer for retrieving and caching dividend history data.

    Implements the cache staleness strategy: fresh data (< 7 days) is returned
    immediately, stale data (7–30 days) is returned with a background refresh
    scheduled, and expired data (> 30 days) blocks on a synchronous re-scrape
    before returning.

    Attributes:
        stock_repo: The repository used for database access.
    """

    def __init__(self, stock_repo: StockRepoDependency) -> None:
        """Initialize the service with an injected stock repository.

        Args:
            stock_repo: The StockRepository instance, provided by FastAPI's
                dependency injection.
        """
        self.stock_repo: StockRepository = stock_repo

    async def _insert_new_stock(self, ticker: str) -> Stock:
        """Scrape a ticker for the first time and persist all data.

        Calls the scraper to retrieve stock info, dividend metrics, and the
        full dividend history, then inserts everything as a new Stock record.

        Args:
            ticker: The ticker symbol to scrape and insert.

        Returns:
            Stock: The newly created and persisted Stock ORM instance.
        """
        stock_dividend_info = await async_get_dividend_info(ticker)

        stock = await self.stock_repo.insert_new_stock(*stock_dividend_info)

        return stock

    async def get_dividend_history(
        self, ticker: str, background_tasks: BackgroundTasks
    ) -> StockDividendHistoryResponse:
        """Retrieve the dividend history for a ticker, respecting cache freshness.

        If the ticker has never been seen, performs a full scrape. If cached
        data exists, the response depends on its age:
        - Fresh (< 7 days): returns cached data immediately.
        - Stale (7–30 days): returns cached data and schedules a background
          refresh.
        - Expired (>= 30 days): blocks on a synchronous re-scrape, then
          returns the updated data.

        Args:
            ticker: The ticker symbol to look up.
            background_tasks: FastAPI BackgroundTasks instance for scheduling
                deferred refreshes.

        Returns:
            StockDividendHistoryResponse: The dividend history response,
                validated from the Stock ORM model via Pydantic.
        """
        stock = await self.stock_repo.get_stock(ticker)

        if stock is None:
            new_stock = await self._insert_new_stock(ticker)
            await self.stock_repo.commit()

            return StockDividendHistoryResponse.model_validate(new_stock)

        stock_date_refresh = stock.date_refreshed.replace(tzinfo=UTC)

        if datetime.now(UTC) - stock_date_refresh < timedelta(days=7):
            return StockDividendHistoryResponse.model_validate(stock)

        if (
            timedelta(days=7)
            <= datetime.now(UTC) - stock_date_refresh
            < timedelta(days=30)
        ):
            background_tasks.add_task(_update_dividend_history, ticker)

            return StockDividendHistoryResponse.model_validate(stock)

        if datetime.now(UTC) - stock_date_refresh >= timedelta(days=30):
            await _do_refresh(ticker, self.stock_repo)
            await self.stock_repo.commit()

        return StockDividendHistoryResponse.model_validate(stock)


DividendHistoryServiceDependency = Annotated[
    DividendHistoryService, Depends(DividendHistoryService)
]
