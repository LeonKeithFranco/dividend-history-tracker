from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture, MockFixture

from scraper import DividendHistory, DividendMetrics, StockInfo


@pytest.fixture
def mock_async_get_dividend_info(
    mocker: MockerFixture,
    mock_scraper_response: tuple[StockInfo, DividendMetrics, DividendHistory],
) -> MagicMock:
    from app.domain import service

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

        first_response = client.get(f"/dividend/{ticker}")
        assert first_response.status_code == status.HTTP_200_OK
        mock_async_get_dividend_info.assert_called_once_with(ticker)

        second_response = client.get(f"/dividend/{ticker}")
        assert second_response.status_code == status.HTTP_200_OK
        mock_async_get_dividend_info.assert_called_once()

        assert first_response.json()["events"] == second_response.json()["events"]
