from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.domain import service
from scraper import DividendHistory, DividendMetrics, StockInfo
from scraper.errors import (
    ScraperTimeoutError,
    ScraperUnavailableError,
    TickerNotFoundError,
)


@pytest.fixture
def mock_async_get_dividend_info(
    mocker: MockerFixture,
    mock_scraper_response: tuple[StockInfo, DividendMetrics, DividendHistory],
) -> MagicMock:
    return mocker.patch.object(
        service,
        "async_get_dividend_info",
        return_value=mock_scraper_response,
    )


class TestGetDividendHistory:
    def test_cache_miss_scrapes_and_returns_200(
        self,
        client: TestClient,
        mock_async_get_dividend_info: MagicMock,
    ) -> None:
        ticker = "AAPL"

        response = client.get(f"/dividends/{ticker}")

        mock_async_get_dividend_info.assert_called_once_with(ticker)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        assert data["ticker_symbol"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert data["exchange"] == "NASDAQ"
        assert len(data["events"]) == 2

    def test_cache_hit_fresh_does_not_scrape(
        self,
        client: TestClient,
        mock_async_get_dividend_info: MagicMock,
    ) -> None:
        ticker = "AAPL"

        first_response = client.get(f"/dividends/{ticker}")
        assert first_response.status_code == status.HTTP_200_OK
        mock_async_get_dividend_info.assert_called_once_with(ticker)

        second_response = client.get(f"/dividends/{ticker}")
        assert second_response.status_code == status.HTTP_200_OK
        mock_async_get_dividend_info.assert_called_once()

        assert first_response.json()["events"] == second_response.json()["events"]

    def test_invalid_ticker_returns_404(
        self, client: TestClient, mocker: MockerFixture
    ) -> None:
        invalid_ticker = "INVLD"

        mocker.patch.object(
            service,
            "async_get_dividend_info",
            side_effect=TickerNotFoundError(f"Ticker '{invalid_ticker}' not found"),
        )

        response = client.get(f"dividends/{invalid_ticker}")
        assert "detail" in response.json()

    def test_scraper_timeout_returns_504(
        self, client: TestClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            service,
            "async_get_dividend_info",
            side_effect=ScraperTimeoutError("Timed out loading page."),
        )

        response = client.get("/dividends/AAPL")

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert "detail" in response.json()

    def test_scraper_unavailable_returns_503(
        self, client: TestClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            service,
            "async_get_dividend_info",
            side_effect=ScraperUnavailableError("Driver crashed"),
        )

        response = client.get("/dividends/AAPL")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "detail" in response.json()
