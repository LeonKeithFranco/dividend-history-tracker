class ScraperError(Exception):
    """Base error for all scraper errors."""


class TickerNotFoundError(ScraperError):
    """The ticker symbol doesn't exist in dividendhistory.org."""


class TickerHasNoDividends(ScraperError):
    """The stock does not have any dividends associated with it."""


class ScraperTimeoutError(ScraperError):
    """The site didn't respond in time retry may help."""


class ScraperUnavailableError(ScraperError):
    """Site returned 5xx or a known outage state."""


class ParseError(ScraperError):
    """Got a response, but couldn't parse it as expected."""
