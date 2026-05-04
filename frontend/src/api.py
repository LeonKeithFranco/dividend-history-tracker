from types import TracebackType
from typing import Self

import httpx

from src.settings import get_settings


class BackendAPI:
    """HTTP client for communicating with the FastAPI backend.

    Wraps an httpx.Client configured with the backend's base URL and timeout.
    Intended to be used as a context manager so the underlying connection is
    properly closed after use.

    Attributes:
        client: The underlying httpx.Client instance.
    """

    def __init__(self, timeout: float | None = None) -> None:
        """Initialize the client with an optional timeout override.

        Args:
            timeout: Request timeout in seconds. Defaults to the value from
                application settings if not provided.
        """
        t = get_settings().api_timeout if timeout is None else timeout

        self.client = httpx.Client(
            base_url=get_settings().api_base_url,
            timeout=t,
        )

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            BackendAPI: The BackendAPI instance itself.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and close the HTTP connection.

        Args:
            exc_type: The exception type if an exception occurred, None otherwise.
            exc_val: The exception value if an exception occurred, None otherwise.
            exc_tb: The exception traceback if an exception occurred, None otherwise.
        """
        self.client.close()

    def get_dividend_history(self, ticker: str) -> httpx.Response:
        """Fetch the dividend history for a ticker from the backend API.

        Args:
            ticker: The stock ticker symbol to look up.

        Returns:
            httpx.Response: The raw HTTP response from the backend. The caller
                is responsible for checking the status code and parsing the body.
        """
        response = self.client.get(f"/dividends/{ticker}")

        return response
