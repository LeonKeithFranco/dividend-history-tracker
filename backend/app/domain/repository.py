from dataclasses import asdict
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from database.db.session import get_db
from database.models import DividendEvent, DividendMetric, Stock
from scraper import DividendEvent as ScraperDividendEvent
from scraper import DividendHistory, DividendMetrics, StockInfo

DbDependency = Annotated[AsyncSession, Depends(get_db)]


class StockRepository:
    def __init__(self, db: DbDependency) -> None:
        self.db: AsyncSession = db

    async def commit(self) -> None:
        await self.db.commit()

    async def get_stock(self, ticker: str) -> Stock | None:
        query = (
            select(Stock)
            .outerjoin(Stock.events)
            .where(Stock.ticker_symbol == ticker)
            .options(
                contains_eager(Stock.events),
                selectinload(Stock.metric),
            )
            .order_by(DividendEvent.ex_dividend_date.asc())
        )
        results = await self.db.execute(query)
        return results.scalar_one_or_none()

    async def insert_new_stock(
        self,
        stock_info: StockInfo,
        dividend_metrics: DividendMetrics,
        dividend_history: DividendHistory,
    ) -> Stock:
        stock = Stock(**asdict(stock_info))
        stock.metric = DividendMetric(**asdict(dividend_metrics))
        stock.events = [
            DividendEvent(**asdict(event)) for event in dividend_history.dividend_events
        ]

        self.db.add(stock)
        await self.db.flush()

        # Refresh with eager loading to avoid MissingGreenlet error during Pydantic validation
        await self.db.refresh(stock, attribute_names=["metric", "events"])

        return stock

    async def insert_new_dividend_events(
        self, stock: Stock, events: list[ScraperDividendEvent]
    ) -> None:
        stock.events.extend([DividendEvent(**asdict(event)) for event in events])

        await self.db.flush()
        await self.db.refresh(stock, attribute_names=["metric", "events"])


StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
