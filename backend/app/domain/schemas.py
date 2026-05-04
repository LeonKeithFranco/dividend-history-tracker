from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DividendEventSchema(BaseModel):
    """Pydantic schema for a single dividend event in an API response.

    Attributes:
        ex_dividend_date: The date on which the stock traded ex-dividend.
        payout_date: The date on which the dividend was paid.
        cash_amount: The per-share dividend amount.
        pct_change: The percentage change from the previous dividend, or None
            if not available.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    ex_dividend_date: date
    payout_date: date
    cash_amount: Decimal
    pct_change: float | None


class StockDividendHistoryResponse(BaseModel):
    """Pydantic response model for the GET /dividends/{ticker} endpoint.

    Validated directly from a Stock ORM instance via from_attributes.

    Attributes:
        company_name: The full name of the company.
        ticker_symbol: The stock's exchange ticker symbol.
        exchange: The exchange the stock is listed on.
        date_refreshed: The UTC timestamp of the last data refresh.
        events: The complete list of dividend events for this stock.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    company_name: str
    ticker_symbol: str
    exchange: str
    date_refreshed: datetime
    events: list[DividendEventSchema]
