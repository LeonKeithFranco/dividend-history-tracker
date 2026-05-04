from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from scraper import DividendHistory, DividendMetrics, StockInfo


class TestGetDividendHistory:
    def test_cache_miss_scarpes_and_returns_200(
        self,
        client: TestClient,
        mocker: MockerFixture,
        mock_scraper_response: tuple[StockInfo, DividendMetrics, DividendHistory],
    ) -> None:
        mock_async_get_dividend_info = mocker.patch(
            "app.domain.service.async_get_dividend_info",
            return_value=mock_scraper_response,
        )

        ticker = "AAPL"

        response = client.get(f"/dividends/{ticker}")

        mock_async_get_dividend_info.assert_called_once_with(ticker)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        assert data["ticker_symbol"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert data["exchange"] == "NASDAQ"
        assert len(data["events"]) == 2
