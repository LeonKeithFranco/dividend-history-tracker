from app.domain.repository import StockRepoDependency, StockRepository
from app.domain.schemas import StockDividendHistoryReponse
from database.models import Stock
from scraper import get_dividend_info


class DividendHistoryService:
    def __init__(self, stock_repo: StockRepoDependency) -> None:
        self.stock_repo: StockRepository = stock_repo

    async def _insert_new_stock(self, ticker: str) -> Stock:
        get_dividend_info(ticker)
        stock = await self.stock_repo.insert_new_stock(*get_dividend_info(ticker))

        return stock

    async def get_dividend_history(self, ticker: str) -> StockDividendHistoryReponse:
        stock = await self.stock_repo.get_stock(ticker)

        if stock is None:
            new_stock = await self._insert_new_stock(ticker)

            await self.stock_repo.db.commit()

            return StockDividendHistoryReponse.model_validate(new_stock)
