from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from log_manager import Logger, log
from utils import HTMLCleaner
from browser import BaseCrawler
from models import *

from typing import Callable, Dict
import json
import re


class GungCrawler(BaseCrawler):
    def __init__(self, config_key, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        """
        Initialize the Selenium WebDriver with custom options.
        This method automatically installs the Chrome WebDriver if not already installed, using ChromeDriverManager.

        :param headless: If True, the browser is run in headless mode, which means it operates without a GUI.
        :param no_images: If True, the browser will not load images, which can speed up web page loading times.
        :param keep_window: If True, the browser window will not automatically close after execution.
        """
        super().__init__(headless, no_images, keep_window)
        self.config = self.load_config(config_key)
        self.constants = self.load_config("constants")

    @staticmethod
    def load_config(config_key):
        with open("config.json") as f:
            config = json.load(f)
        return config[config_key]

    def parse_table(self, table_object: WebElement, column_type: list) -> list[PreviewItem]:
        """
        Iterate through the rows of the table and parse the data.
        :param table_object: selenium object of the table
        :param column_type: list of column types
        :return: dictionary of the table
        """

        # Validate column types
        valid_column_types = ["", "article_id", "title_url", "title_js_url", "date"]
        if not all(col_type in valid_column_types for col_type in column_type):
            raise ValueError("Invalid column type.")

        def parse_js_url(column: WebElement) -> str:
            """
            Get the emulated URL from the JavaScript call
            :param column: column object
            :return:
            """
            js_call = column.find_element(By.TAG_NAME, "a").get_attribute("href")
            argument_match = re.search(r"fn_egov_inqire_notice\('(\d+)'\);", js_call)
            if not argument_match:
                raise ValueError("Invalid JavaScript call format")

            # domain + js_url
            base_url = self.config["domain"] + self.constants["js_url"]
            return base_url + argument_match.group(1)

        table_data = []

        # Iterate through table rows
        for row in table_object.find_elements(By.TAG_NAME, "tr"):
            columns = row.find_elements(By.XPATH, "./*")

            rowitem = PreviewItem()

            for i, col_type in enumerate(column_type):
                log.debug(f"{i} Column type: {col_type}")
                log.debug(f"{i} Column text: {columns[i].text}")
                if i >= len(columns):
                    break
                if col_type == "":
                    continue
                try:
                    if col_type == "title_js_url":
                        rowitem.set_title(columns[i].text)
                        rowitem.set_url(parse_js_url(columns[i]))
                    if col_type == "title_url":
                        rowitem.set_url(columns[i].find_element(By.TAG_NAME, "a").get_attribute("href"))
                        rowitem.set_title(columns[i].text)
                    if col_type == "article_id":
                        rowitem.set_article_id(int(columns[i].text))
                    if col_type == "date":
                        rowitem.set_time(columns[i].text)
                except Exception as e:
                    log.debug(f"Invalid row. Error: {e}")
                    break
            if rowitem.is_valid():
                table_data.append(rowitem)
        return table_data

    def fetch_main(self) -> list[PreviewItem]:
        """
        Fetch the main page of the website
        :return: list of articles in list of dictionaries.
        """
        self.get(self.config["url"] + "1")
        main_table = self.element_from_xpath(self.config["table"])
        return self.parse_table(main_table, self.config["table_column"])

    def last_article_id(self) -> int:
        """
        Fetch the last article id of the website
        :return: last article id
        """
        table = self.fetch_main()
        return table[0].article_id

    def last_page_number(self) -> int:
        """
        Fetch the last page number of the website
        :return: last page number
        """
        article_count = self.last_article_id()
        return article_count // self.config["articles_per_page"] + 1

    def fetch_article_list(self, page: int = 1) -> list[PreviewItem]:
        """
        Fetch the article list page of the website
        :param page: page number to fetch
        :return: list of articles in list of dictionaries.
        :raises: ValueError if the page number is less than 1.
        :raises: OutOfBoundsException if the page number is out of bounds.
        """
        if page < 1:
            raise ValueError("Page number must be greater than 0")
        if page > self.last_page_number():
            raise ValueError("Page number is out of bounds")

        self.get(self.config["url"] + str(page))
        list_table = self.element_from_xpath(self.config["table"])
        return self.parse_table(list_table, self.config["table_column"])

    def fetch_article_list_range(self, page_start: int = 1, page_end: int = None) -> list[PreviewItem]:
        """
        Fetch the article list page of the website in a range.
        :param page_start: starting page number to fetch (inclusive).
        :param page_end: ending page number to fetch (inclusive). When not specified, it defaults to the last page.
        :return: list of articles in list of dictionaries.
        :raises: ValueError if the page number is less than 1.
        :raises: ValueError if starting page number is greater than the ending page number.
        :raises: OutOfBoundsException if the page number is out of bounds.
        """
        if page_start < 1:
            raise ValueError("Starting page number must be greater than 0")
        if page_end:
            if page_end < 1:
                raise ValueError("Ending page number must be greater than 0")
            if page_start > page_end:
                raise ValueError("Starting page number cannot be greater than the ending page number")
        else:
            page_end = self.last_page_number()

        master_list = []
        for page in range(page_start, page_end + 1):
            master_list += self.fetch_article_list(page)
        return master_list

    def fetch_article_until(self, article_id: int, max_ceiling: int = 500) -> list[PreviewItem]:
        """
        Fetch the article list page of the website until the article id is found.
        :param article_id: article id to search for
        :param max_ceiling: maximum number of pages to search for
        :return: list of articles in list of dictionaries.
        :raises: ValueError if the article id is less than 1.
        :raises: OutOfBoundsException if the article id is out of bounds.
        """
        if article_id < 1:
            raise ValueError("Article ID must be greater than 0")
        if article_id > self.last_article_id():
            raise ValueError(f"Article ID is out of bounds. Last article ID: {self.last_article_id()}")

        master_list = []
        for page in range(1, max_ceiling + 1):
            master_list += self.fetch_article_list(page)
            if master_list[-1].article_id < article_id:
                break

        # delete articles after the article id
        for i, article in enumerate(master_list):
            if article.article_id < article_id:
                del master_list[i:]
                break

        return master_list

    def get_article_body(self, url: str) -> str:
        """
        Get the article body from the url with the minimal HTML structure
        :param url: url of the article
        :return: article body in minimal HTML structure
        """
        self.get(url)
        article_html = self.element_from_xpath(self.config["article_container"]).get_attribute("innerHTML")
        # Clean HTML using HTMLCleaner
        clean_html = HTMLCleaner().clean_html(article_html)
        return clean_html

    def get_article(self, item: PreviewItem) -> Article:
        """
        Get the article from the PreviewItem
        :param item: PreviewItem object
        :return: Article object
        """
        article_body = self.get_article_body(item.url)
        return Article(source_prefix=self.config["source_prefix"], article_id=item.article_id, source_url=item.url,
                       title=item.title, time=item.time, content=article_body)


class GyeongbokgungCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("gyeongbokgung", headless, no_images, keep_window)


class ChanggyeonggungCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("changgyeonggung", headless, no_images, keep_window)


class ChangdeokgungCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("changdeokgung", headless, no_images, keep_window)


class JongmyoCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("jongmyo", headless, no_images, keep_window)


class DeoksugungEventsCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("deoksugung_events", headless, no_images, keep_window)


class DeoksugungNoticeCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("deoksugung_notice", headless, no_images, keep_window)


class RoyalTombsNoticeCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("royal_tombs_notice", headless, no_images, keep_window)


class RoyalTombsEventsCrawler(GungCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("royal_tombs_events", headless, no_images, keep_window)


if __name__ == "__main__":
    Logger(debug=False)

    # article_url = input("URL: ")
    # article_url = "https://www.royalpalace.go.kr/content/board/view.asp?seq=970&page=&c1=&c2="

    with GyeongbokgungCrawler() as crawler:
        result = crawler.fetch_article_list_range(1, 2)

        for item in result:
            document = crawler.get_article(item)
            print(document)
