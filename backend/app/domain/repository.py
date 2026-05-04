from dataclasses import asdict
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from database.db.session import get_db
from database.models import DividendEvent, DividendMetric, Stock
from scraper import DividendEvent as ScraperDividendEvent
from scraper import DividendHistory, DividendMetrics, StockInfo

DbDependency = Annotated[AsyncSession, Depends(get_db)]


class StockRepository:
    """Data-access layer for Stock, DividendMetric, and DividendEvent records.

    Wraps an async SQLAlchemy session and provides domain-oriented query and
    persistence methods. Callers are responsible for committing the session
    via the commit method after writes.

    Attributes:
        db: The underlying async SQLAlchemy session.
    """

    def __init__(self, db: DbDependency) -> None:
        """Initialize the repository with a database session.

        Args:
            db: An async SQLAlchemy session, provided by FastAPI's dependency
                injection via get_db.
        """
        self.db: AsyncSession = db

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def get_stock(self, ticker: str) -> Stock | None:
        """Look up a stock by ticker symbol with its events and metric eagerly loaded.

        Uses contains_eager for events (via an explicit outerjoin) and
        selectinload for the metric to avoid MissingGreenlet errors in async
        contexts.

        Args:
            ticker: The ticker symbol to search for.

        Returns:
            Stock: The matching Stock instance with relationships loaded, or
                None if no stock with that ticker exists.
        """
        query = (
            select(Stock)
            .outerjoin(Stock.events)
            .where(Stock.ticker_symbol == ticker)
            .options(
                contains_eager(Stock.events),
                selectinload(Stock.metric),
            )
            # .order_by(DividendEvent.ex_dividend_date.asc())
        )
        results = await self.db.execute(query)
        return results.unique().scalar_one_or_none()

    async def insert_new_stock(
        self,
        stock_info: StockInfo,
        dividend_metrics: DividendMetrics,
        dividend_history: DividendHistory,
    ) -> Stock:
        """Create a new Stock record with its metric and full event history.

        Converts scraper dataclasses into ORM models, flushes to the database
        to generate primary keys, and refreshes the relationships so they are
        available for Pydantic serialization without triggering lazy loads.

        Args:
            stock_info: The stock's identifying information from the scraper.
            dividend_metrics: The stock's current dividend metrics.
            dividend_history: The complete list of historical dividend events.

        Returns:
            Stock: The newly created Stock instance with relationships loaded.
        """
        stock = Stock(**asdict(stock_info))
        stock.metric = DividendMetric(**asdict(dividend_metrics))
        stock.events = [
            DividendEvent(**asdict(event)) for event in dividend_history.dividend_events
        ]

        self.db.add(stock)
        await self.db.flush()

        # Refresh with eager loading to avoid MissingGreenlet error during Pydantic validation
        await self.db.refresh(stock, attribute_names=["metric", "events"])

        return stock

    async def insert_new_dividend_events(
        self, stock: Stock, events: list[ScraperDividendEvent]
    ) -> None:
        """Append new dividend events to an existing stock's history.

        Converts scraper DividendEvent dataclasses into ORM models, extends the
        stock's events list, and refreshes the relationships after flushing.

        Args:
            stock: The existing Stock instance to add events to.
            events: The new dividend events from the scraper to persist.
        """
        stock.events.extend([DividendEvent(**asdict(event)) for event in events])

        await self.db.flush()
        await self.db.refresh(stock, attribute_names=["metric", "events"])


StockRepoDependency = Annotated[StockRepository, Depends(StockRepository)]
