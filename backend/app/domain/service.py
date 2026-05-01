from app.domain.repository import StockRepoDependency, StockRepository


class DividendHistoryService:
    def __init__(self, stock_repo: StockRepoDependency) -> None:
        self.stock_repo: StockRepository = stock_repo
