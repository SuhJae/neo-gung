from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from log_manager import Logger, log
from models import *
from browser import BaseCrawler

from typing import Callable, Dict
import json
import re

from bs4 import BeautifulSoup, NavigableString


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

        def parse_js_url(column: WebElement) -> Dict[str, str]:
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
            print(base_url)
            return {"title": column.text, "url": base_url + argument_match.group(1)}

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
            "title_js_url": parse_js_url,
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
                if i >= len(columns):
                    break
                if col_type == "":
                    continue
                try:
                    row_data.update(column_parsers[col_type](columns[i]))
                except Exception as e:
                    log.debug(f"Invalid row. Error: {e}")
                    row_data = {}
                    break

            if row_data:
                table_data.append(
                    PreviewItem(article_id=row_data["article_id"], title=row_data["title"], url=row_data["url"],
                                time=row_data["date"]))

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

    def fetch_article_list_range(self, page_start: int = 1, page_end: int = None) -> list[dict]:
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

    def fetch_article_until(self, article_id: int, max_ceiling: int = 500) -> list[dict]:
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
            if master_list[-1]["article_id"] <= article_id:
                break

        # delete articles after the article id
        for i, article in enumerate(master_list):
            if article["article_id"] < article_id:
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


class HTMLCleaner:
    def __init__(self):
        self.soup = None

    def set_soup(self, html_content):
        """Set the soup object from HTML content."""
        self.soup = BeautifulSoup(html_content, 'html.parser')

    def merge_formatting_tags(self, soup):
        """
        Merge adjacent formatting tags (like <b>, <i>, <strong>, etc.) if they are redundant.
        """
        for tag in soup.find_all(['b', 'i', 'strong', 'em']):  # Add more tags if needed
            next_sibling = tag.find_next_sibling()
            if next_sibling and tag.name == next_sibling.name and tag.attrs == next_sibling.attrs:
                tag.string = (tag.string or '') + (next_sibling.string or '')
                next_sibling.decompose()
                # Recursively check for further adjacent tags
                self.merge_formatting_tags(soup)

    def merge_with_next_sibling(self, tag):
        """
        Merge a tag with its next sibling if they are of the same type and have the same attributes.
        """
        next_sibling = tag.next_sibling
        while next_sibling and isinstance(next_sibling, NavigableString) and not next_sibling.strip():
            next_sibling = next_sibling.next_sibling

        if next_sibling and tag.name == next_sibling.name and tag.attrs == next_sibling.attrs:
            tag.string = (tag.get_text() or '') + (next_sibling.get_text() or '')
            next_sibling.decompose()
            self.merge_with_next_sibling(tag)  # Check again in case there are more than two adjacent tags

    def remove_empty_tags(self):
        """
        Remove empty tags from the soup.
        """
        if hasattr(self, 'soup'):
            for tag in self.soup.find_all():
                if not tag.get_text(strip=True):
                    tag.decompose()
        else:
            raise AttributeError("Soup object not found in class instance.")

    def clean_html(self, html_content) -> str:
        self.soup = BeautifulSoup(html_content, 'html.parser')

        # Remove scripts, styles, and non-essential attributes
        [tag.decompose() for tag in self.soup(['script', 'style'])]

        # Remove or unwrap unnecessary tags and attributes
        for tag in self.soup.find_all():
            if tag.name == 'a':
                tag.attrs = {'href': tag.get('href')}  # Keep href attribute for 'a' tags
            elif tag.name == 'img':
                tag.attrs = {'src': tag.get('src')}  # Keep src attribute for 'img' tags
            else:
                tag.attrs = {}

        # Unwrap or decompose div tags
        for div in self.soup.find_all('div'):
            div.unwrap()  # or div.decompose() to completely remove div and its content

        # Remove spans by unwrapping them
        for span in self.soup.find_all('span'):
            span.unwrap()

        # Call the function to merge adjacent tags
        self.merge_formatting_tags(self.soup)

        # Remove empty tags
        self.remove_empty_tags()

        # Prepare minimal HTML structure
        minimal_html = self.soup.new_tag('html')
        head = self.soup.new_tag('head')
        meta = self.soup.new_tag('meta', charset='UTF-8')
        head.append(meta)
        minimal_html.append(head)
        body = self.soup.new_tag('body')
        body.append(self.soup)
        minimal_html.append(body)

        # Convert to string
        result_html = str(minimal_html)
        # normalize spaces using regex
        result_html = re.sub(r"\s+", " ", result_html)
        return result_html


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
        result = crawler.fetch_main()
        arti = crawler.get_article(result[0])

    print(arti)
