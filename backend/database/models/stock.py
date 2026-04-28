from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.event import DividendEvent
    from database.models.metric import DividendMetric


class Stock(Base):
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
