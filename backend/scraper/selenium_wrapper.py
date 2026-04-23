from typing import Literal, Self, cast

from selenium import webdriver
from selenium.webdriver import chrome, firefox
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

type _WebDriver = chrome.webdriver.WebDriver | firefox.webdriver.WebDriver


class SeleniumWrapper:
    """A wrapper around Selenium WebDriver for simplified browser automation.

    This class provides a simplified interface to Selenium Webdriver, handling
    driver initialization and providing common methods.

    Attributes:
        driver: The underlying Selenium WebDriver instance.
    """

    def __init__(self, browser: Literal["chrome", "firefox"] = "chrome") -> None:
        """Initialized the Selenium wrapper with the specified browser.

        Args:
            browser: The browser to use. Must either be "chrome" or "firefox".

        Raises:
            TypeError: If browser is not "chrome" or "firefox".
        """
        match browser:
            case "chrome":
                chrome_options = chrome.options.Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(options=chrome_options)
            case "firefox":
                firefox_options = firefox.options.Options()
                firefox_options.add_argument("--headless")

                driver = webdriver.Firefox(options=firefox_options)

        self.driver: _WebDriver = driver

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            SeleniumWrapper: The SeleniumWrapper instance itself.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the context manager and close the browser.

        Args:
            exc_type: The exception type if an exception occurred, None otherwise.
            exc_val: The exception value if an exception occurred, None otherwise.
            exc_tb: The exception traceback if an exception occurred, None otherwise.

        Returns:
            bool: False to propagate exceptions.
        """
        self.driver.quit()
        return False

    def open_page(self, url: str) -> None:
        """Navigate to the specified URL in the browser.

        Args:
            url: The URL to navigate to.
        """
        self.driver.get(url)

    def get_html_page(self) -> str:
        """The the full HTML source of the current page.

        Returns:
            str: The entire HTML of the page as a string.
        """
        return self.driver.page_source

    def find_element_with_wait(
        self, by: str, value: str, timeout: float = 10.0
    ) -> WebElement:
        wait = WebDriverWait(driver=self.driver, timeout=timeout)

        element = wait.until(EC.presence_of_element_located((by, value)))

        return element

    def get_html(self, by: str, value: str) -> str:
        """Get the HTML of an element located by the specified method.

        Args:
            by: A locator strategy from selenium.webdriver.common.by.By
                (e.g, By.ID, By.XPATH, By.CSS_SELECTOR).
            value: The locator value used with the specified strategy.

        Returns:
            str: The outer HTML of the located element as a string.

        Raises:
            NoSuchElementException: If no element is found matching the locator.
        """
        element = self.find_element_with_wait(by, value)
        return cast(str, element.get_attribute("outerHTML"))
