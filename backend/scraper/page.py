from selenium.webdriver.common.by import By

from scraper.selenium_wrapper import SeleniumWrapper


class DividendHistoryPage:
    _STOCK_INFO_EXPATH = "//h1[contains(@class, 'title-with-badge')]"
    _DIVIDEN_METRICS_TABLE_XPATH = "//h2[text()='Dividend Metrics']/../..//dl"
    _DIVIDEND_HISTORY_TABLE_XPATH = "//div[@id='tabulator-table-body']"
    _NEXT_BUTTON_XPATH = "//button[@title='Next Page']"

    def __init__(self, driver: SeleniumWrapper) -> None:
        self.driver: SeleniumWrapper = driver

    def get_stock_info_html(self) -> str:
        return self.driver.get_html(By.XPATH, self._STOCK_INFO_EXPATH)

    def get_dividend_metrics_table_html(self) -> str:
        return self.driver.get_html(By.XPATH, self._DIVIDEN_METRICS_TABLE_XPATH)

    def get_dividend_events_table_html(self) -> str:
        return self.driver.get_html(By.XPATH, self._DIVIDEND_HISTORY_TABLE_XPATH)

    def is_next_button_enabled(self) -> bool:
        return self.driver.is_element_enabled(By.XPATH, self._NEXT_BUTTON_XPATH)

    def click_next_button(self) -> None:
        self.driver.click_element(By.XPATH, self._NEXT_BUTTON_XPATH)
