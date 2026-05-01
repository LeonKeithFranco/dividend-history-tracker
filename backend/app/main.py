from fastapi import BackgroundTasks, FastAPI

from app.domain.schemas import StockDividendHistoryResponse
from app.domain.service import DividendHistoryServiceDependency

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello world"}


@app.get("/dividends/{stock}", response_model=StockDividendHistoryResponse)
async def get_dividend_history(
    stock: str,
    service: DividendHistoryServiceDependency,
    backgrounds_tasks: BackgroundTasks,
):
    return await service.get_dividend_history(stock, backgrounds_tasks)
