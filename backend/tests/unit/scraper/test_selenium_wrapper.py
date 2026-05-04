import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from scraper.selenium_wrapper import SeleniumWrapper


class TestSeleniumWrapper:
    """Tests for the SeleniumWrapper utility methods.

    Each test runs against a locally served copy of the AAPL dividend history
    page (opened automatically by the _setup fixture) so no external network
    access is required.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, selenium_wrapper: SeleniumWrapper, local_web_server: str):
        """Opens up the local version of the AAPL dividend history page."""
        selenium_wrapper.open_page(url=local_web_server)

    def test_page_landing(self, selenium_wrapper: SeleniumWrapper):
        element = selenium_wrapper.driver.find_element(
            By.XPATH, "//a[@class='navbar-brand']"
        )

        assert element.text == "Dividend History"

    def test_get_html_page(self, selenium_wrapper: SeleniumWrapper):
        html = selenium_wrapper.get_html_page()

        assert "<html" in html and "</html>" in html

    def test_get_html(self, selenium_wrapper: SeleniumWrapper):
        elem_html = selenium_wrapper.get_html(By.XPATH, "//a[@class='navbar-brand']")

        assert "<a" in elem_html and "</a>" in elem_html

    def test_find_element_non_existent_element(self, selenium_wrapper: SeleniumWrapper):
        with pytest.raises(TimeoutException):
            selenium_wrapper.find_element_with_wait(
                By.XPATH, "//a[@class='navbar']", timeout=1
            )
