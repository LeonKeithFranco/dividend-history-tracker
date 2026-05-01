from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.stock import Stock


class DividendMetric(Base):
    """ORM model representing the current dividend metrics for a stock.

    Holds a snapshot of the key dividend-related figures for a stock at the time of the
    most recent data refresh. Each stock at has at most one associated metric record.

    Attributes:
        id: Auto-incremented primary key inherited from Base.
        yield_: The dividend yield as a percentage.
        payout_ratio: The proportion of earnings paid out as a divdends, expressed as a
            percentage.
        frequency: The dividend payment frequency (e.g. "Monthly", "Quareterly").
        annual_dividend: The total annual dividend per share.
        next_ex_dividend_date: The next date on which a buyer must own the stock to be
            entitled to the upcoming dividend.
        next_payout_date: The date on which the next dividend payment will be made.
        stock_id: Foreign key referencing the parent stock record.
        stocl: The parent Stock instance this metric belongs to.
    """

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
        unique=True,
    )

    stock: Mapped["Stock"] = relationship(
        back_populates="metric",
    )
