import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from bs4 import BeautifulSoup
from selenium.common import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

from scraper.errors import (
    ParseError,
    ScraperTimeoutError,
    ScraperUnavailableError,
    TickerHasNoDividends,
    TickerNotFoundError,
)
from scraper.page import DividendHistoryPage
from scraper.selenium_wrapper import SeleniumWrapper


@dataclass(frozen=True, slots=True)
class StockInfo:
    """Information about a stock."""

    company_name: str
    ticker_symbol: str
    exchange: str


@dataclass(frozen=True, slots=True)
class DividendMetrics:
    """Metrics related to a stocks dividend history."""

    yield_: float
    pay_out_ratio: float
    frequency: str
    annual_dividend: Decimal
    next_ex_dividend_date: date
    next_payout_date: date


@dataclass(frozen=True, slots=True)
class DividendEvent:
    """A single dividend history event."""

    ex_dividend_date: date
    payout_date: date
    cash_amount: Decimal
    pct_change: float | None


@dataclass(frozen=True, slots=True)
class DividendHistory:
    """A collection of dividend events."""

    dividend_events: list[DividendEvent] = field(default_factory=list)


_DATE_FORMAT = "%Y-%m-%d"
_MAX_RETRIES = 3


def _extract(val: str, pattern: str) -> str | None:
    """Extract a substring matching a regex pattern.

    Args:
        val: The string to search.
        pattern: The regex pattern to match.

    Returns:
        str: The matched substring, or None if no match is found.
    """
    match = re.search(
        pattern=pattern,
        string=val,
    )

    return match.group() if match is not None else None


def _extract_number(val: str) -> str | None:
    """Extract a numeric value, including decimals, from a string.

    Args:
        val: The string to search.

    Returns:
        str: The extracted numeric value as a string, or None if no
            match is found.
    """
    return _extract(val=val, pattern=r"-?\d+(\.\d+)?")


def _extract_date(val: str) -> str | None:
    """Extract a date substring with the format YYYY-MM-DD from a string.

    Args:
        val: The string to search.

    Returns:
        str: The extract date substring, or None if no match is found.
    """
    return _extract(val=val, pattern=r"\d{4}-\d{2}-\d{2}")


def _parse_pct_change(val: str) -> float | None:
    """Parse a percentage from the "% Change" column of the dividend history table.

    Args:
        val: The string to search.

    Returns:
        float: The parsed percentage value as a string, or None if val is empty,
            or if not match is found.
    """
    if val == "":
        return None

    num = _extract_number(val)

    return float(num) if num is not None else None


def _parse_pct(val: str) -> float:
    """Parse a percentage value from a string.

    Args:
        val: The string to parse. Must contain a numeric value.

    Raises:
        ValueError: If no numeric value can be extracted from the string.
    """
    return float(cast(str, _extract_number(val)))


def _parse_cash_amount(val: str) -> Decimal:
    """Parse a cash amount from a string.

    Args:
        val: The string to parse. Must contain a numeric value.

    Returns:
        Decimal: The parsed cash amount.

    Raises:
        ValueError: If no numeric value can be extracted from the string.
    """
    return Decimal(cast(str, _extract_number(val)))


def _get_stock_info(dividend_history_page: DividendHistoryPage) -> StockInfo:
    """Extract stock information from the dividend history page.

    Args:
        dividend_history_page: The DividendHistoryPage instance to extract stock
            information from.

    Returns:
        StockInfo: A StockInfo object containing the company name, ticker symbol,
            and exchange.

    Raises:
        TickerNotFoundError: If the stock information element is not found on the page.
    """
    try:
        stock_info_html = dividend_history_page.get_stock_info_html()
    except TimeoutException as e:
        raise TickerNotFoundError from e

    stock_info_soup = BeautifulSoup(stock_info_html, "html.parser")

    stock_strings = list(stock_info_soup.stripped_strings)

    return StockInfo(
        company_name=stock_strings[0],
        ticker_symbol=stock_strings[1],
        exchange=stock_strings[2],
    )


def _get_dividend_metrics(
    dividend_history_page: DividendHistoryPage,
) -> DividendMetrics:
    """Extract dividend metrics from the dividend history page.

    Args:
        dividend_history_page: The DividendHistoryPage instance to extract metrics from.

    Returns:
        DividendMetrics: A DividendMetrics object containing yield, payout ratio,
            frequency, annual dividend, and the next ex-dividend and payout dates.

    Raises:
        TickerHasNoDividends: If the dividend metrics table is not found on the page.
    """
    try:
        dividend_metrics_table_html = (
            dividend_history_page.get_dividend_metrics_table_html()
        )
    except TimeoutException as e:
        raise TickerHasNoDividends(
            "Stock has no associated dividends or metrics table has not loaded"
        ) from e

    dividend_metrics_table_soup = BeautifulSoup(
        dividend_metrics_table_html, "html.parser"
    )

    metrics_text = [
        metric.text.strip() for metric in dividend_metrics_table_soup.find_all("dd")
    ]

    return DividendMetrics(
        yield_=_parse_pct(metrics_text[0]),
        pay_out_ratio=_parse_pct(metrics_text[2]),
        frequency=metrics_text[3],
        annual_dividend=_parse_cash_amount(metrics_text[4]),
        next_ex_dividend_date=datetime.strptime(
            cast(str, _extract_date(metrics_text[5])),
            _DATE_FORMAT,
        ).date(),
        next_payout_date=datetime.strptime(
            cast(str, _extract_date(metrics_text[6])),
            _DATE_FORMAT,
        ).date(),
    )


def _get_dividend_history(dividend_events_table_html: str) -> DividendHistory:
    """Extract dividend history events from an HTML table.

    Parses the dividend history table HTML and creates DividendEvent objects for
    each row in the table.

    Args:
        dividend_events_table_html: The HTML string containing the dividend
            events table.

    Returns:
        DividendHistory: A DividendHistory object containing the extracted
            dividend events.
    """
    history = DividendHistory()

    dividend_history_table_soup = BeautifulSoup(
        dividend_events_table_html, "html.parser"
    )
    for row in dividend_history_table_soup.find_all("div", class_="tabulator-row"):
        cells_text = [
            cell.text.strip() for cell in row.find_all("div", class_="tabulator-cell")
        ]

        history.dividend_events.append(
            DividendEvent(
                ex_dividend_date=datetime.strptime(cells_text[0], _DATE_FORMAT).date(),
                payout_date=datetime.strptime(cells_text[1], _DATE_FORMAT).date(),
                cash_amount=_parse_cash_amount(cells_text[2]),
                pct_change=_parse_pct_change(cells_text[3]),
            )
        )

    return history


def _get_complete_dividend_history(
    dividend_history_page: DividendHistoryPage,
) -> DividendHistory:
    """Retrieve the complete dividend history by handling pagination.

    Fetches the dividend history table and automatically navigates through all
    pages of results by clicking the next button, accumulating all dividend
    events into a single DividendHistory object.

    Args:
        dividend_history_page: The DividendHistoryPage instance to extract
            dividend history from.

    Returns:
        DividendHistory: A DividendHistory object containing all dividend events
            across all pages.

    Raises:
        TickerHasNoDividends: If the dividend history table is not found on the page.
    """
    try:
        dividend_events_table_html = (
            dividend_history_page.get_dividend_events_table_html()
        )
        dividend_history = _get_dividend_history(dividend_events_table_html)
        while dividend_history_page.is_next_button_enabled():
            dividend_history_page.click_next_button()

            dividend_events_table_html = (
                dividend_history_page.get_dividend_events_table_html()
            )
            dividend_history.dividend_events.extend(
                _get_dividend_history(dividend_events_table_html).dividend_events
            )

        return dividend_history
    except TimeoutException as e:
        raise TickerHasNoDividends(
            "Stock has no associated dividends or dividend history table has not loaded"
        ) from e


def _open_page(driver: SeleniumWrapper, url: str) -> None:
    """Navigate to a URL with automatic retry logic.

    Attempts to open the specified URL with exponential backoff retry on failure.
    Raises ScraperTimeoutError for timeout failures and ScraperUnavailableError
    for driver-related failures.

    Args:
        driver: The SeleniumWrapper instance to use for navigation.
        url: The URL to navigate to.

    Raises:
        ScraperTimeoutError: If the page fails to load within the timeout period
            after all retry attempts.
        ScraperUnavailableError: If the WebDriver encounters an error after all
            retry attempts.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            driver.open_page(url)
            break
        except (TimeoutException, WebDriverException) as e:
            if attempt < _MAX_RETRIES:
                time.sleep(2**attempt)
                continue

            match e:
                case TimeoutException():
                    raise ScraperTimeoutError("Page could not load.") from e
                case WebDriverException():
                    raise ScraperUnavailableError from e


def get_dividend_info(
    ticker: str,
) -> tuple[StockInfo, DividendMetrics, DividendHistory]:
    """Retrieve comprehensive dividend information for a given stock ticker.

    This function automates the scraping of the dividend history page from the
    corresponding page on dividendhistory.org. Scrapes the stock details, dividend
    metrics table, and dividend history table. Handles pagination automatically.

    Args:
        ticker: The ticker symbol of to retrieve dividend information for.

    Returns:
        tuple:
            - StockInfo: Information about the stock
            - DividendMetrics: Current dividend metrics and upcoming dividend dates.
            - DividendHistory: Complete historical record of dividend events.
    """
    DIVIDEND_HISTORY_URL = f"https://dividendhistory.org/payout/{ticker.upper()}/"

    with SeleniumWrapper() as driver:
        _open_page(driver, DIVIDEND_HISTORY_URL)

        dividend_history_page = DividendHistoryPage(driver)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                stock_info = _get_stock_info(dividend_history_page)
                dividend_metrics = _get_dividend_metrics(dividend_history_page)
                dividend_history = _get_complete_dividend_history(dividend_history_page)
                break
            except StaleElementReferenceException as e:
                if attempt < _MAX_RETRIES:
                    continue

                raise ParseError("could not parse element on page") from e

    return (stock_info, dividend_metrics, dividend_history)
