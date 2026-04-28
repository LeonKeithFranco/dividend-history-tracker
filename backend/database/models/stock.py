from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.event import DividendEvent
    from database.models.metric import DividendMetric


class Stock(Base):
    """ORM model representing a tracked stock.

    Serves as the root entity in the data model, with a one-to-one relationship to its
    current dividend metrics and one-to-many relationship to its full dividend history.

    Attributes:
        id: Auto-incremented primary key inherited from Base.
        company_name: The full legal name of the company.
        ticker_symbol: The stock's exchange ticker symbol. Unique across all stocks.
        exchange: The exchange the stock is listed on (e.g. NYSE, NASDAQ).
        date_refreshed: The UTC timestamp of the last data refresh. Defaults to the time
            the row was inserted.
        metric: The associated DividendMetric record for this stock.
        events: The list of DividendEvent records belonging to this stock.
    """

    __tablename__ = "stocks"

    company_name: Mapped[str] = mapped_column(
        String(100),
    )
    ticker_symbol: Mapped[str] = mapped_column(
        String(5),
        unique=True,
    )
    exchange: Mapped[str] = mapped_column(
        String(10),
    )
    date_refreshed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    metric: Mapped["DividendMetric"] = relationship(
        back_populates="stock",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["DividendEvent"]] = relationship(
        back_populates="stock",
        cascade="all, delete-orphan",
    )
