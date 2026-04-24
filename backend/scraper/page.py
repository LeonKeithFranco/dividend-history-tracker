from selenium.webdriver.common.by import By

from scraper.selenium_wrapper import SeleniumWrapper


class DividendHistoryPage:
    """A page object for interacting with the dividend history page.

    This class provides a simplified interface for extracting and navigating
    the dividend history page using Selenium. Abstracts away usage of XPaths
    into semantic methods.

    Attributes:
        driver: The SeleniumWrapper instance used to interact with the page.
    """

    _STOCK_INFO_XPATH = "//h1[contains(@class, 'title-with-badge')]"
    _DIVIDEN_METRICS_TABLE_XPATH = "//h2[text()='Dividend Metrics']/../..//dl"
    _DIVIDEND_HISTORY_TABLE_XPATH = "//div[@id='tabulator-table-body']"
    _NEXT_BUTTON_XPATH = "//button[@title='Next Page']"

    def __init__(self, driver: SeleniumWrapper) -> None:
        """Initialize DividendHistoryPage with a SeleniumWrapper instance.

        Args:
            driver: An instance of SeleniumWrapper for driving the page interactions.
        """
        self.driver: SeleniumWrapper = driver

    def get_stock_info_html(self) -> str:
        """Get the HTML of the stock h1 element.

        Returns:
            str: The outer HTML of the stock h1 element as a string.

        Raises:
            NoSuchElementException: If the stock info element is not found.
        """
        return self.driver.get_html(By.XPATH, self._STOCK_INFO_XPATH)

    def get_dividend_metrics_table_html(self) -> str:
        """Get the HTML of the dividend metrics table.

        Returns:
            str: The outer HTML of the dividend metrics table as a string.

        Raises:
            NoSuchElementException: If the dividend metrics table is not found.
        """
        return self.driver.get_html(By.XPATH, self._DIVIDEN_METRICS_TABLE_XPATH)

    def get_dividend_events_table_html(self) -> str:
        """Get the HTML of the dividend history events table.

        Returns:
            str: The outer HTML of the dividend events table as a string.

        Raises:
            NoSuchElementException: If the dividend events table is not found.
        """
        return self.driver.get_html(By.XPATH, self._DIVIDEND_HISTORY_TABLE_XPATH)

    def is_next_button_enabled(self) -> bool:
        """Check if the next page button is enabled.

        Returns:
            bool: True if the next button is enabled, False otherwise.

        Raises:
            NoSuchElementException: If the next button is not found.
        """
        return self.driver.is_element_enabled(By.XPATH, self._NEXT_BUTTON_XPATH)

    def click_next_button(self) -> None:
        """Click the next page button to navigate to the next page of results.

        Raises:
            NoSuchElementException: If the next button is not found.
        """
        self.driver.click_element(By.XPATH, self._NEXT_BUTTON_XPATH)
