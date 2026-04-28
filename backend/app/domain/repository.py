from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.db.session import get_db

DbDependency = Annotated[AsyncSession, Depends(get_db)]


class StockRepository:
    def __init__(self, db: DbDependency) -> None:
        self.db: AsyncSession = db


StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
