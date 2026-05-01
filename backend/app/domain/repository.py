from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db.session import get_db
from database.models import Stock

DbDependency = Annotated[AsyncSession, Depends(get_db)]


class StockRepository:
    def __init__(self, db: DbDependency) -> None:
        self.db: AsyncSession = db

    async def get_stock_info(self, ticker: str) -> Stock | None:
        query = select(Stock).where(Stock.ticker_symbol == ticker)
        results = await self.db.execute(query)

        return results.scalar_one_or_none()


StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
