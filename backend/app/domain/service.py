from app.domain.repository import StockRepoDependency, StockRepository
from app.domain.schemas import StockDividendHistoryResponse
from database.models import Stock
from scraper import async_get_dividend_info


class DividendHistoryService:
    def __init__(self, stock_repo: StockRepoDependency) -> None:
        self.stock_repo: StockRepository = stock_repo

    async def _insert_new_stock(self, ticker: str) -> Stock:
        stock_dividend_info = await async_get_dividend_info(ticker)

        stock = await self.stock_repo.insert_new_stock(*stock_dividend_info)

        return stock

    async def get_dividend_history(self, ticker: str) -> StockDividendHistoryResponse:
        stock = await self.stock_repo.get_stock(ticker)

        if stock is None:
            new_stock = await self._insert_new_stock(ticker)

            await self.stock_repo.commit()

            return StockDividendHistoryResponse.model_validate(new_stock)

        # TODO: flesh out rest of logic
