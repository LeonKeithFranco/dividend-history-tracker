from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.stock import Stock


class DividendEvent(Base):
    """ORM model representing a single historical dividend event for a stock.

    Each record captures the details of one dividend payout. The combination of stock and
    ex-dividend date is unique, preventing duplicate events from being inserted on
    subsequent refreshes.

    Attributes:
        id: Auto-incremented primary key inherited from Base.
        ex_dividend_date: The date on which the stock began trading without the right to
            the dividend.
        payout_date: The date on which the dividend was paid to shareholders.
        cash_amount: The per-share cash dividend amount.
        pct_change: The percentage change in dividend amount relative to the prior event.
            None if the first recorded event or the change is not available.
        stock_id: Foreign key referencing the parent Stock record.
        stock: The parent stock instance this event belongs to.
    """

    __tablename__ = "events"

    ex_dividend_date: Mapped[date]
    payout_date: Mapped[date]
    cash_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
    )
    pct_change: Mapped[float | None]

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        index=True,
    )

    stock: Mapped["Stock"] = relationship(
        back_populates="events",
    )

    __table_args__ = (
        UniqueConstraint("stock_id", "ex_dividend_date", name="uq_event_stock_date"),
    )
