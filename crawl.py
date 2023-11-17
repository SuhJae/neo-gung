from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec

from log_manager import Logger, log
from typing import Callable, Dict
import json
import re


class BaseCrawler:
    def __init__(self, config_key, headless: bool = False, no_images: bool = True, keep_window: bool = False) -> None:
        """
        Initialize the Selenium WebDriver with custom options.
        This method automatically installs the Chrome WebDriver if not already installed, using ChromeDriverManager.

        :param headless: If True, the browser is run in headless mode, which means it operates without a GUI.
        :param no_images: If True, the browser will not load images, which can speed up web page loading times.
        :param keep_window: If True, the browser window will not automatically close after execution.
        """
        self.headless = headless
        self.no_images = no_images
        self.keep_window = keep_window
        self.config = self.load_config(config_key)

        options = Options()
        if headless:
            options.add_argument("--headless")
        if no_images:
            options.add_argument("--blink-settings=imagesEnabled=false")
        if keep_window:
            options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    @staticmethod
    def load_config(config_key):
        with open("config.json") as f:
            config = json.load(f)
        return config[config_key]

    @staticmethod
    def parse_table(table_object: WebElement, column_type: list) -> list[dict]:
        """
        Iterate through the rows of the table and parse the data.
        :param table_object: selenium object of the table
        :param column_type: list of column types
        :return: dictionary of the table
        """

        # Validate column types
        valid_column_types = ["", "article_id", "title_url", "title_cgg_url", "date"]
        if not all(col_type in valid_column_types for col_type in column_type):
            raise ValueError("Invalid column type.")

        def parse_cgg_url(column: WebElement) -> Dict[str, str]:
            """
            Get the emulated URL from the JavaScript call
            :param column: column object
            :return:
            """
            js_call = column.find_element(By.TAG_NAME, "a").get_attribute("href")
            argument_match = re.search(r"fn_egov_inqire_notice\('(\d+)'\);", js_call)
            if not argument_match:
                raise ValueError("Invalid JavaScript call format")

            full_url = (
                "https://cgg.cha.go.kr/agapp/public/bbs/selectBoardArticle.do?bbsId=BBSMSTR_000000000195&bbsTyCode"
                "=BBST03&bbsAttrbCode=BBSA03&nttId=")
            return {"title": column.text, "url": full_url + argument_match.group(1)}

        # Parsing functions
        def parse_article_id(column: WebElement) -> Dict[str, int]:
            return {"article_id": int(column.text)}

        def parse_title_url(column: WebElement) -> Dict[str, str]:
            return {"title": column.text, "url": column.find_element(By.TAG_NAME, "a").get_attribute("href")}

        def parse_date(column: WebElement) -> Dict[str, str]:
            return {"date": column.text}

        # Map column types to their respective parsing functions
        column_parsers: Dict[str, Callable[[WebElement], any]] = {
            "article_id": parse_article_id,
            "title_url": parse_title_url,
            "title_cgg_url": parse_cgg_url,
            "date": parse_date
        }

        table_data = []

        # Iterate through table rows
        for row in table_object.find_elements(By.TAG_NAME, "tr"):
            row_data = {}
            columns = row.find_elements(By.XPATH, "./*")

            for i, col_type in enumerate(column_type):
                log.debug(f"{i} Column type: {col_type}")
                log.debug(f"{i} Column text: {columns[i].text}")
                if i >= len(columns) or col_type == "":
                    break
                try:
                    row_data.update(column_parsers[col_type](columns[i]))
                except Exception as e:
                    log.error(f"Invalid row. Error: {e}")
                    row_data = {}
                    break

            if row_data:
                table_data.append(row_data)

        return table_data

    def fetch_main(self) -> list[dict]:
        """
        Fetch the main page of the website
        :return: list of articles in list of dictionaries.
        """
        self.get(self.config["main_url"])
        main_table = self.element_from_xpath(self.config["table"])
        return self.parse_table(main_table, self.config["table_column"])

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


class ChanggyeonggungCrawler(BaseCrawler):
    def __init__(self, headless: bool = False, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("changgyeonggung", headless, no_images, keep_window)


class DeoksugungCrawler(BaseCrawler):
    def __init__(self, headless: bool = False, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("deoksugung", headless, no_images, keep_window)


class GyeongbokgungCrawler(BaseCrawler):
    def __init__(self, headless: bool = False, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("gyeongbokgung", headless, no_images, keep_window)


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
        if source_prefix and source_prefix not in ["cdg", "cgg", "dsg-e", "dsg-n", "gbg", "jm"]:
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


if __name__ == "__main__":
    Logger(debug=False)
    gyeongbokgung = GyeongbokgungCrawler()
    # changdeokgung = ChangdeokgungCrawler()
    # changgyeonggung = ChanggyeonggungCrawler()

    result = gyeongbokgung.fetch_main()

    with open("result.json", "w") as file:
        json.dump(result, file, ensure_ascii=False, indent=4)

    # input("Press Enter to exit...")
