from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base

if TYPE_CHECKING:
    from database.models.stock import Stock


class DividendEvent(Base):
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
