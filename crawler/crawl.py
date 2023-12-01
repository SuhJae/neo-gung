import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from crawler.log_manager import Logger, log
from crawler.utils import HTMLCleaner, no_stopword
from crawler.browser import BaseCrawler
from crawler.models import *
from crawler.db import DatabaseManager, ElasticsearchClient
from formatting import format_notice
from typing import Union

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
        self.config_key = config_key
        self.last_article_id_cache = None

    @staticmethod
    def load_config(config_key):
        with open("config.json") as f:
            config = json.load(f)
        return config[config_key]

    def get_config_key(self) -> str:
        return self.config_key

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
            base_url = self.config["domain"] + self.config["js_url"]
            return base_url + argument_match.group(1)

        table_data = []

        # Iterate through table rows
        for row in table_object.find_elements(By.TAG_NAME, "tr"):
            columns = row.find_elements(By.XPATH, "./*")

            rowitem = PreviewItem()

            for i, col_type in enumerate(column_type):
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
        if not self.last_article_id_cache:
            table = self.fetch_main()
            self.last_article_id_cache = table[0].article_id
        return self.last_article_id_cache

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
        log.info(f"Fetching page {page}")
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
            if master_list[-1].article_id <= article_id:
                break

        # delete articles after the article id
        for i, article in enumerate(master_list):
            if article.article_id < article_id:
                del master_list[i:]
                break

        return master_list

    def fetch_article_in_range(self, article_id_start: int, article_id_end: int) -> list[PreviewItem]:
        """
        Fetch the article list page of the website in a range.
        :param article_id_start: starting article id to fetch (inclusive).
        :param article_id_end: ending article id to fetch (inclusive).
        :return: list of PreviewItems
        """

        if article_id_start < 1 or article_id_end < 1:
            raise ValueError("Article IDs must be greater than 0")
        if article_id_start > article_id_end:
            raise ValueError("Starting article ID cannot be greater than the ending article ID")
        if article_id_end > self.last_article_id():
            raise ValueError(f"Ending article ID is out of bounds. Last article ID: {self.last_article_id()}")

        master_list = []

        # calculate the page number for the starting and ending articles
        initial_page = (self.last_article_id() - article_id_end) // self.config["articles_per_page"] + 1
        final_page = (self.last_article_id() - article_id_start) // self.config["articles_per_page"] + 1

        # fetch the articles in the range
        for page in range(initial_page, final_page + 1):
            log.info(f"Fetching article {page}")
            master_list += self.fetch_article_list(page)

        # filter out articles outside the desired ID range
        master_list = [article for article in master_list if article_id_start <= article.article_id <= article_id_end]

        return master_list

    def get_article_body(self, url: str, load_page: bool = True) -> str:
        """
        Get the article body from the url with the minimal HTML structure
        :param url: url of the article
        :param load_page: if True, load the page before getting the article body
        :return: article body in minimal HTML structure
        """
        if load_page:
            self.get(url)
        # get innerHTML and textContent of the article container
        article_html = self.element_from_xpath(self.config["article_container"]).get_attribute("innerHTML")
        # Clean HTML using HTMLCleaner
        clean_html = HTMLCleaner().html_to_markdown(article_html, self.config["domain"])
        return clean_html

    def get_article(self, item: PreviewItem, load_page: bool = True) -> Article:
        """
        Get the article from the PreviewItem
        :param item: PreviewItem object
        :param load_page: if True, load the page before getting the article body
        :return: Article object
        """
        article_body = self.get_article_body(item.url, load_page)

        return Article(source_prefix=self.config["source_prefix"], article_id=item.article_id, source_url=item.url,
                       title=item.title, time=item.time, content=article_body)

    def get_articles(self, items: list[PreviewItem], max_workers: int = 5) -> list[Article]:
        article_list = []
        tabs = []
        item_index = 0

        max_workers = min(max_workers, len(items))

        # Open initial tabs
        for i in range(max_workers):
            if i < len(items):
                log.info(f"Gathering article {items[i].article_id}")
                tabs.append(self.get_url_in_new_tab(items[item_index].url, str(item_index)))
                item_index += 1

        while len(tabs) > 0:
            self.switch_to_tab(tabs[0])
            if self.element_from_xpath_exists(self.config["article_container"]):

                try:
                    article_list.append(self.get_article(items[int(tabs[0])], False))
                except Exception as e:
                    log.error(f"Error getting article: {e} (URL: {items[int(tabs[0])].url})")

                # close the current tab
                self.close_current_tab()
                del tabs[0]

                # open a new tab if there are more items
                if item_index < len(items):
                    self.switch_to_tab(tabs[0])
                    log.info(f"Gathering article {items[item_index].article_id}")
                    tabs.append(self.get_url_in_new_tab(items[item_index].url, str(item_index)))
                    item_index += 1
            else:
                # move the first item to the end of the list
                tabs.append(tabs[0])
                del tabs[0]

        time.sleep(1)
        return article_list

    def get_cache(self, article: PreviewItem) -> Union[Article, None]:
        """
        Get the cache of the article from local storage (cache folder)
        :param article: Article object
        :return: cache of the article
        """
        # check if the article is cached
        if not os.path.exists(f"cache/{self.config_key}/{article.article_id}.md"):
            # if not, get the article and cache it
            return None

        with open(f"cache/{self.config_key}/{article.article_id}.md", "r", encoding="utf-8") as f:
            return Article(source_prefix=self.config["source_prefix"], article_id=article.article_id,
                           source_url=article.url, title=article.title, time=article.time, content=f.read())


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


def save_to_cache(crawler):
    # result = crawler.fetch_article_in_range(270, 280)
    index_result = crawler.fetch_article_until(1)
    # index_result = crawler.fetch_article_list_range(1, 2)
    articles = crawler.get_articles(index_result, max_workers=5)

    for document in articles:
        if len(document.content) > 16000:
            log.info(f"Skipping article {document.article_id} due to length")
        elif not no_stopword(document.content):
            log.info(f"Skipping article {document.article_id} due to stopword")
        else:
            log.info(f"Formatting article {document.article_id}")

            try:
                formatted = format_notice(document.content)
            except Exception as e:
                log.error(f"Error formatting article {document.article_id}: {e}")
                continue

            with open(f"cache/{crawler.get_config_key()}/{document.article_id}.md", "w", encoding="utf-8") as f:
                f.write(formatted)


if __name__ == "__main__":
    Logger(debug=False)
    save_to_cache(RoyalTombsNoticeCrawler())
    save_to_cache(RoyalTombsEventsCrawler())

    # db = DatabaseManager()
    # es = ElasticsearchClient()

    # es.setup_index()

    # with GyeongbokgungCrawler() as crawler:
    #     result = crawler.fetch_article_until(1)
    #     for preview_item in result:
    #         article_item = crawler.get_cache(preview_item)
    #         if article_item:
    #             log.info(f"Inserting: {article_item.article_id}")
    #             db.insert_article(article_item)
    #
    # with ChanggyeonggungCrawler() as crawler:
    #     result = crawler.fetch_article_until(1)
    #     for preview_item in result:
    #         article_item = crawler.get_cache(preview_item)
    #         if article_item:
    #             log.info(f"Inserting: {article_item.article_id}")
    #             db.insert_article(article_item)
    #
    # with ChangdeokgungCrawler() as crawler:
    #     result = crawler.fetch_article_until(1)
    #     for preview_item in result:
    #         article_item = crawler.get_cache(preview_item)
    #         if article_item:
    #             log.info(f"Inserting: {article_item.article_id}")
    #             db.insert_article(article_item)
