import json
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pytest_mock import MockFixture
from selenium.common import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

import scraper.scraper as scraper_module
from scraper import DividendEvent, DividendHistory, get_dividend_info
from scraper.errors import (
    ParseError,
    ScraperTimeoutError,
    ScraperUnavailableError,
    TickerHasNoDividends,
    TickerNotFoundError,
)
from scraper.page import DividendHistoryPage
from scraper.scraper import _MAX_RETRIES, DividendMetrics, StockInfo
from scraper.selenium_wrapper import SeleniumWrapper


@pytest.fixture
def _aapl_dividend_history_from_json() -> DividendHistory:
    with open(
        Path(__file__).parent.parent.parent / "fixtures" / "aapl_dividend_history.json",
        "r",
    ) as f:
        data = json.load(f)

    events = [
        DividendEvent(
            ex_dividend_date=date.fromisoformat(event["ex_dividend_date"]),
            payout_date=date.fromisoformat(event["payout_date"]),
            cash_amount=Decimal(event["cash_amount"]),
            pct_change=event["pct_change"],
        )
        for event in data["dividend_history"]["dividend_events"]
    ]

    return DividendHistory(dividend_events=events)


class TestScraper:
    @pytest.mark.live
    def test_scrape_ko_ticker_live(self):
        """Tests the live version of the dividendhistory.org page for the Coca Cola
            company.

        This test was written on 2026-04-25 but assumes that Coca Cola will be an
        on-going concern, and therefore the test is written to try and account for
        future dividend events.
        """
        stock_info, dividend_metrics, dividend_history = get_dividend_info("KO")

        assert stock_info.company_name == "Coca Cola"
        assert stock_info.ticker_symbol == "KO"
        assert stock_info.exchange == "NYSE"

        assert dividend_metrics.yield_ > 0
        assert dividend_metrics.pay_out_ratio > 0
        assert dividend_metrics.frequency == "Quarterly"
        assert (
            dividend_metrics.next_payout_date >= dividend_metrics.next_ex_dividend_date
        )

        # 257 is the current number of dividend events at time of writing this test
        assert len(dividend_history.dividend_events) >= 257

        for i in range(1, len(dividend_history.dividend_events)):
            # verify events are in reverse chronological order
            assert (
                dividend_history.dividend_events[i - 1].ex_dividend_date
                > dividend_history.dividend_events[i].ex_dividend_date
            )

        for div_event in dividend_history.dividend_events:
            assert div_event.payout_date >= div_event.ex_dividend_date

        for i, div_event in enumerate(dividend_history.dividend_events):
            if div_event.pct_change is not None:
                current_dividend = div_event.cash_amount
                previous_dividend = dividend_history.dividend_events[i + 1].cash_amount
                calculated_pct_change = (
                    (current_dividend / previous_dividend - 1) * 100
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                assert Decimal(str(div_event.pct_change)) == calculated_pct_change

        assert (
            dividend_metrics.annual_dividend
            == dividend_history.dividend_events[0].cash_amount * 4
        )
        assert (
            dividend_metrics.next_ex_dividend_date
            == dividend_history.dividend_events[1].ex_dividend_date
        )
        assert (
            dividend_metrics.next_payout_date
            == dividend_history.dividend_events[1].payout_date
        )

    def test_scrape_aapl_ticker_offline(
        self,
        mocker: MockFixture,
        local_web_server: str,
        _aapl_dividend_history_from_json: DividendHistory,
    ):
        """Tests a downloaded version of the AAPL page on dividendhistory.org.

        This test uses mocking to redirect to the local downloaded version of the APPL
        page.
        """
        from scraper.selenium_wrapper import SeleniumWrapper

        original_open_page = SeleniumWrapper.open_page

        def modified_open_page(self, url):
            original_open_page(self, local_web_server)

        mocker.patch.object(
            SeleniumWrapper,
            "open_page",
            new=modified_open_page,
        )

        stock_info, dividend_metrics, dividend_history = get_dividend_info("AAPL")

        assert stock_info.ticker_symbol == "AAPL"
        assert stock_info.company_name == "Apple"
        assert stock_info.exchange == "Nasdaq"

        assert dividend_metrics.yield_ == 0.38
        assert dividend_metrics.pay_out_ratio == 13.16
        assert dividend_metrics.frequency == "Quarterly"
        assert dividend_metrics.annual_dividend == Decimal("1.04")
        assert (
            dividend_metrics.next_ex_dividend_date
            == datetime.strptime("2026-05-12", "%Y-%m-%d").date()
        )
        assert (
            dividend_metrics.next_payout_date
            == datetime.strptime("2026-05-15", "%Y-%m-%d").date()
        )

        for actual_event, expected_event in zip(
            dividend_history.dividend_events,
            _aapl_dividend_history_from_json.dividend_events,
        ):
            assert actual_event == expected_event


class TestScraperOpenPage:
    """Failure-mode tests for the open_page call.

    These tests mock SeleniumWrapper.open_page so that no real browser starts and no real
    network request is made. Each test controls what the mocked open_page does (raise,
    raise-then-succeed, etc) and then asserts how get_dividend_info behaves on top of it.
    """

    def test_open_page_raises_scraper_timeout_after_exhausting_retries(
        self, mocker: MockFixture
    ):
        mocker.patch("scraper.scraper.time.sleep")

        mock_open_page = mocker.patch(
            "scraper.selenium_wrapper.SeleniumWrapper.open_page"
        )
        mock_open_page.side_effect = TimeoutException("fake timeout")

        with pytest.raises(ScraperTimeoutError) as exc_info:
            get_dividend_info("AAPL")

        assert isinstance(exc_info.value.__cause__, TimeoutException)

        assert mock_open_page.call_count == _MAX_RETRIES

    def test_open_page_raises_scraper_unavailable_on_webdriver_error(
        self, mocker: MockFixture
    ):
        mocker.patch("scraper.scraper.time.sleep")

        mock_open_page = mocker.patch(
            "scraper.selenium_wrapper.SeleniumWrapper.open_page"
        )
        mock_open_page.side_effect = WebDriverException("fake driver error")

        with pytest.raises(ScraperUnavailableError) as exc_info:
            get_dividend_info("AAPL")

        assert isinstance(exc_info.value.__cause__, WebDriverException)
        assert mock_open_page.call_count == _MAX_RETRIES

    def test_open_page_succeeds_after_transient_timeout(self, mocker: MockFixture):
        mocker.patch("scraper.scraper.time.sleep")

        mock_open_page = mocker.patch(
            "scraper.selenium_wrapper.SeleniumWrapper.open_page"
        )
        mock_open_page.side_effect = [TimeoutException("1"), None]

        sentinel_stock_info = StockInfo(
            company_name="Apple", ticker_symbol="AAPL", exchange="Nasdaq"
        )
        sentinel_metrics = DividendMetrics(
            yield_=0.38,
            pay_out_ratio=13.16,
            frequency="Quarterly",
            annual_dividend=Decimal("1.04"),
            next_ex_dividend_date=date(2026, 5, 12),
            next_payout_date=date(2026, 5, 15),
        )
        sentinel_history = DividendHistory(dividend_events=[])

        mocker.patch.object(
            scraper_module, "_get_stock_info", return_value=sentinel_stock_info
        )
        mocker.patch.object(
            scraper_module, "_get_dividend_metrics", return_value=sentinel_metrics
        )
        mocker.patch.object(
            scraper_module,
            "_get_complete_dividend_history",
            return_value=sentinel_history,
        )

        stock_info, dividend_metrics, dividend_history = get_dividend_info("AAPL")

        assert mock_open_page.call_count == 2
        assert stock_info is sentinel_stock_info
        assert dividend_metrics is sentinel_metrics
        assert dividend_history is sentinel_history

    def test_stock_info_timeout_raises_ticker_not_found(self, mocker: MockFixture):
        mocker.patch.object(SeleniumWrapper, "open_page")
        mock_get_stock_info_html = mocker.patch.object(
            DividendHistoryPage,
            "get_stock_info_html",
            side_effect=TimeoutException("stock info not found"),
        )

        with pytest.raises(TickerNotFoundError):
            get_dividend_info("FAKE")

        assert mock_get_stock_info_html.call_count == 1


class TestStockMetrics:
    def test_metrics_timeout_raises_ticker_has_no_dividends(self, mocker: MockFixture):
        mocker.patch.object(SeleniumWrapper, "open_page")
        mocker.patch.object(
            DividendHistoryPage,
            "get_stock_info_html",
            return_value=(
                "<h1 class='title-with-badge'>"
                "<span>Berkshire Hathaway</span><span>BRK.A</span><span>NYSE</span>"
                "</h1>"
            ),
        )
        mock_get_dividend_metrics_table_html = mocker.patch.object(
            DividendHistoryPage,
            "get_dividend_metrics_table_html",
            side_effect=TimeoutException("metrics table not found"),
        )

        with pytest.raises(TickerHasNoDividends):
            get_dividend_info("BRK.A")

        assert mock_get_dividend_metrics_table_html.call_count == 1


class TestStaleElements:
    def test_stale_element_retries_then_raises_parse_error(self, mocker: MockFixture):
        mocker.patch.object(SeleniumWrapper, "open_page")
        mock_get_stock_info = mocker.patch.object(
            scraper_module,
            "_get_stock_info",
            side_effect=StaleElementReferenceException("stale element"),
        )

        with pytest.raises(ParseError):
            get_dividend_info("AAPL")

        assert mock_get_stock_info.call_count == _MAX_RETRIES

    def test_stale_element_recovers_on_retry(self, mocker: MockFixture):
        mocker.patch.object(SeleniumWrapper, "open_page")

        sentinel_stock_info = StockInfo(
            company_name="Apple", ticker_symbol="AAPL", exchange="Nasdaq"
        )
        sentinel_metrics = DividendMetrics(
            yield_=0.38,
            pay_out_ratio=13.16,
            frequency="Quarterly",
            annual_dividend=Decimal("1.04"),
            next_ex_dividend_date=date(2026, 5, 12),
            next_payout_date=date(2026, 5, 15),
        )
        sentinel_history = DividendHistory(dividend_events=[])

        mocker.patch.object(
            scraper_module,
            "_get_stock_info",
            side_effect=[StaleElementReferenceException("1"), sentinel_stock_info],
        )
        mocker.patch.object(
            scraper_module, "_get_dividend_metrics", return_value=sentinel_metrics
        )
        mocker.patch.object(
            scraper_module,
            "_get_complete_dividend_history",
            return_value=sentinel_history,
        )

        stock_info, _, _ = get_dividend_info("AAPL")

        assert stock_info is sentinel_stock_info
