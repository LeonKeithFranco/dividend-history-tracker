from types import TracebackType
from typing import Self

import httpx

from src.settings import get_settings


class BackendAPI:
    def __init__(self, timeout: float | None = None) -> None:
        t = get_settings().api_timeout if timeout is None else 60.0

        self.client = httpx.Client(
            base_url=get_settings().api_base_url,
            timeout=t,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.client.close()

    def get_dividend_history(self, ticker: str) -> httpx.Response:
        response = self.client.get(f"/dividends/{ticker}")
        response.raise_for_status()

        return response
