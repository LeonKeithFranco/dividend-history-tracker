from fastapi import BackgroundTasks, FastAPI

from app.domain.schemas import StockDividendHistoryResponse
from app.domain.service import DividendHistoryServiceDependency

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello world"}


@app.get("/dividends/{ticker}", response_model=StockDividendHistoryResponse)
async def get_dividend_history(
    ticker: str,
    service: DividendHistoryServiceDependency,
    background_tasks: BackgroundTasks,
):
    return await service.get_dividend_history(ticker, background_tasks)
