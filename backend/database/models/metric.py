from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.stock import Stock


class DividendMetric(Base):
    __tablename__ = "metrics"

    yield_: Mapped[float]
    payout_ratio: Mapped[float]
    frequency: Mapped[str] = mapped_column(
        String(10),
    )
    annual_dividend: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
    )
    next_ex_dividend_date: Mapped[date]
    next_payout_date: Mapped[date]

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        index=True,
    )

    stock: Mapped["Stock"] = relationship(
        back_populates="metric",
    )
