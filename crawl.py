from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from log_manager import Logger, log
import re


class BaseCrawler:
    def __init__(self, headless: bool = False, no_images: bool = True, keep_window: bool = False) -> None:
        """
        Initialize the Selenium WebDriver with custom options.

        :param headless: If True, the browser is run in headless mode, which means it operates without a GUI.
        :param no_images: If True, the browser will not load images, which can speed up web page loading times.
        :param keep_window: If True, the browser window will not automatically close after the script completes execution.

        Example usage:
            # Initialize a WebDriver instance without images and in headless mode
            driver_instance = WebDriver(headless=True, no_images=True, keep_window=False)

        Note: This method automatically installs the Chrome WebDriver if not already installed, using ChromeDriverManager.
        """

        options = Options()
        if headless:
            options.add_argument("--headless")
        if no_images:
            options.add_argument("--blink-settings=imagesEnabled=false")
        if keep_window:
            options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def close_driver(self) -> None:
        """
        Close the driver
        :return: None
        """
        self.driver.close()

    def get(self, url: str) -> None:
        """
        Get the url in the browser
        :param url: url to get
        :return: None
        """
        self.driver.get(url)

    def element_from_xpath(self, element_xpath: str, timeout: int = 10):
        """
        Get the element object for selenium from the xpath
        :param element_xpath: xpath of the element to get
        :param timeout: timeout in seconds
        :return: element object for selenium
        """
        return WebDriverWait(self.driver, timeout).until(ec.presence_of_element_located((By.XPATH, element_xpath)))

    def click_by_xpath(self, element_xpath: str, timeout: int = 10, max_retries: int = 5) -> bool:
        """
        Click the element by xpath
        :param element_xpath: xpath of the element to click
        :param timeout: timeout in seconds
        :param max_retries: max retries to click the element
        :return: True if the element is clicked, False otherwise
        """

        for i in range(max_retries):
            try:
                element = self.element_from_xpath(element_xpath, timeout)
                element.click()
                return True
            except Exception as e:
                log.debug(f"URL: {self.driver.current_url}")
                log.debug(f"Element xpath: {element_xpath}")
                log.warning(f"(Attempt {i + 1}/{max_retries}) Failed to click the element: {e}")
                continue

        log.error(f"Failed to click the element after {max_retries} attempts.")
        return False


class SiteACrawler(BaseCrawler):
    def navigate_to_article(self):
        # Site A specific navigation
        pass

    def extract_data(self):
        # Extract data specific to Site A
        pass

    # ... other Site A specific methods ...


class SiteBCrawler(BaseCrawler):
    def navigate_to_article(self):
        # Site B specific navigation
        pass

    def extract_data(self):
        # Extract data specific to Site B
        pass

    # ... other Site B specific methods ...


class Article:
    def __init__(self, source_prefix: str, article_id: int, source_url: str, title: str, time: str, content: str,
                 attachments: list):
        """
        Initialize a new article instance.

        :param source_prefix: Prefix of the source, one of: "cdg", "cgg", "dsg-e", "dsg-j", "dsg-n", "gbg", "jm".
                              Used to categorize the article's source.
        :param article_id: Unique identifier for the article.
        :param source_url: URL of the article's original source.
        :param title: Title of the article.
        :param time: Timestamp of the article publication time, in the YYYY-MM-DD format.
        :param content: Main content of the article in markdown format.
        :param attachments: List of attachments related to the article, such as images or files.

        :raises ValueError: If the `source_prefix` is not one of the specified valid values.
        :raises ValueError: If the `article_id` is not an integer or less than 1.
        :raises ValueError: If the `time` is not in the YYYY-MM-DD format.
        """

        # Check for errors in the input
        if source_prefix and source_prefix not in ["cdg", "cgg", "dsg-e", "dsg-j", "dsg-n", "gbg", "jm"]:
            raise ValueError(
                "Invalid source prefix. It must be one of: 'cdg', 'cgg', 'dsg-e', 'dsg-j', 'dsg-n', 'gbg', 'jm'.")

        if not article_id or not isinstance(article_id, int) or article_id < 1:
            raise ValueError("Invalid article ID. It must be a positive integer.")

        if not time or not re.match(r"^\d{4}-\d{2}-\d{2}$", time):
            raise ValueError("Invalid time. It must be in the YYYY-MM-DD format.")

        self.source_prefix = source_prefix
        self.article_id = article_id
        self.url = source_url
        self.title = title
        self.time = time
        self.content = content
        self.attachments = attachments


Logger(debug=True)
