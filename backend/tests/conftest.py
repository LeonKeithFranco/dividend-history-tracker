import subprocess
import time
from pathlib import Path
from typing import Iterator

import pytest

from scraper.selenium_wrapper import SeleniumWrapper


@pytest.fixture
def selenium_wrapper() -> Iterator[SeleniumWrapper]:
    """Creates and manages an instance of the SeleniumWrapper class.

    Initializes a SeleniumWrapper instance with a configured browser.
    The underlying WebDriver defaults to a Chrome WebDriver. The instance
    is automatically quit after the test completes, ensuring proper
    resource cleanup.

    Yields:
        SeleniumWrapper: Wrapper around a Selenium WebDriver configured
                         with a headless Chrome WebDrive instance.
    """
    with SeleniumWrapper() as wrapper:
        yield wrapper


@pytest.fixture(scope="session")
def local_web_server() -> Iterator[str]:
    """Creates and manages a local webserver for a downloaded version of
       dividendhistory.org

    A page from dividenhistory.org was downloaded for local and offline
    testing purposes. The page is of the AAPL dividend history. Initializes
    a local web server that serves up only the specified page. The web server
    is cleaned up at the end of the test.

    Yields:
        str: The url of the local web server hosting the AAPL dividend history
             page.
    """
    webpage_folder = Path(__file__).parent / "fixtures" / "dividendhistory_aapl_page"

    server = subprocess.Popen(
        args=["uv", "run", "python", "-m", "http.server", "9000"],
        cwd=webpage_folder,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    yield "http://localhost:9000/"

    server.terminate()
    server.wait()
