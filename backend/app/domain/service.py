from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import BackgroundTasks, Depends

from app.domain.repository import StockRepoDependency, StockRepository
from app.domain.schemas import StockDividendHistoryResponse
from database.db import AsyncSessionFactory
from database.models import Stock
from scraper import async_get_dividend_info
from scraper.scraper import async_get_just_dividend_history


async def _do_refresh(ticker: str, stock_repo: StockRepository):
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
    async with AsyncSessionFactory() as db:
        stock_repo = StockRepository(db)
        await _do_refresh(ticker, stock_repo)
        await stock_repo.commit()


class DividendHistoryService:
    def __init__(self, stock_repo: StockRepoDependency) -> None:
        self.stock_repo: StockRepository = stock_repo

    async def _insert_new_stock(self, ticker: str) -> Stock:
        stock_dividend_info = await async_get_dividend_info(ticker)

        stock = await self.stock_repo.insert_new_stock(*stock_dividend_info)

        return stock

    async def get_dividend_history(
        self, ticker: str, background_tasks: BackgroundTasks
    ) -> StockDividendHistoryResponse:
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
