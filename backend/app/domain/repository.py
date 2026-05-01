from dataclasses import asdict
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db.session import get_db
from database.models import DividendEvent, DividendMetric, Stock
from scraper import DividendHistory, DividendMetrics, StockInfo

DbDependency = Annotated[AsyncSession, Depends(get_db)]


class StockRepository:
    def __init__(self, db: DbDependency) -> None:
        self.db: AsyncSession = db

    async def get_stock(self, ticker: str) -> Stock | None:
        query = select(Stock).where(Stock.ticker_symbol == ticker)
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
        await self.db.refresh(stock)

        return stock


StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
