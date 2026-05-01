from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.schemas import StockDividendHistoryResponse
from app.domain.service import DividendHistoryServiceDependency
from scraper.errors import (
    ParseError,
    ScraperTimeoutError,
    ScraperUnavailableError,
    TickerHasNoDividends,
    TickerNotFoundError,
)

app = FastAPI()


@app.exception_handler(TickerNotFoundError)
async def ticker_not_found_handler(
    request: Request, exc: TickerNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


@app.exception_handler(TickerHasNoDividends)
async def ticket_has_no_dividends_handler(
    request: Request, exc: TickerHasNoDividends
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


@app.exception_handler(ScraperTimeoutError)
async def scraper_timeout_error(
    request: Request, exc: ScraperTimeoutError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": "Data source timed out. Try again later."},
    )


@app.exception_handler(ScraperUnavailableError)
async def scraper_unavailable_handler(
    request: Request, exc: ScraperUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Data source is currently unavailable."},
    )


@app.exception_handler(ParseError)
async def parse_handler(request: Request, exc: ParseError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "Received an unparseable response from the data source."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


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
