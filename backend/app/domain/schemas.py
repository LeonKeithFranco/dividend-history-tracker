from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DividendEventSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    ex_dividend_date: date
    payout_date: date
    cash_amount: Decimal
    pct_change: float | None


class StockDividendHistoryReponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    company_name: str
    ticker_symbol: str
    exchange: str
    date_refreshed: datetime
    dividend_events: list[DividendEventSchema]
