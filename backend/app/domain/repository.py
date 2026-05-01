# from database.models import Stock
# from typing import Annotated

# from fastapi import Depends
# from sqlalchemy.ext.asyncio import AsyncSession

# from database.db.session import get_db

# DbDependency = Annotated[AsyncSession, Depends(get_db)]


# class StockRepository:
#     def __init__(self, db: DbDependency) -> None:
#         self.db: AsyncSession = db


#     async def get_stock_info(self, ticker: str) -> Stock | None:
#         query =


# StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
