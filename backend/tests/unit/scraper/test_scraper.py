import json
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pytest_mock import MockFixture

from scraper.scraper import DividendEvent, DividendHistory, get_dividend_info


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
                previous_divdend = dividend_history.dividend_events[i + 1].cash_amount
                calculated_pct_change = (
                    (current_dividend / previous_divdend - 1) * 100
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

        This test uses mocking to redirect to the local doanloaded version of the APPL
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
