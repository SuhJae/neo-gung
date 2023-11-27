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

from bs4 import BeautifulSoup, NavigableString


class Article:
    def __init__(self, source_prefix: str, article_id: int, source_url: str, title: str, time: str, content: str,
                 attachments: list):
        """
        Initialize a new article instance.

        :param source_prefix: Prefix of the source, Used to categorize the article's source.
        Must be one of: "cdg", "cgg", "dsg-e", "dsg-j", "dsg-n", "gbg", "jm" or "rt".
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
        if source_prefix and source_prefix not in ["cdg", "cgg", "dsg-e", "dsg-n", "gbg", "jm", "rt-n", "rt-e"]:
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

    def __str__(self):
        return f"Article ID: {self.article_id}\n" \
               f"Source URL: {self.url}\n" \
               f"Title: {self.title}\n" \
               f"Time: {self.time}\n" \
               f"Content: {self.content}\n" \
               f"Attachments: {self.attachments}\n"


class BoardEntries:
    def __init__(self, source_prefix: str, entries: list[Article]):
        """
        Initialize a new board entries instance.

        :param source_prefix: Prefix of the source, Used to categorize the article's source.
        Must be one of: "cdg", "cgg", "dsg-e", "dsg-j", "dsg-n", "gbg", "jm" or "rt".
        :param entries: List of articles in the board.
        """

        # Check for errors in the input
        if source_prefix and source_prefix not in ["cdg", "cgg", "dsg-e", "dsg-n", "gbg", "jm", "rt-n", "rt-e"]:
            raise ValueError(
                "Invalid source prefix. It must be one of: 'cdg', 'cgg', 'dsg-e', 'dsg-j', 'dsg-n', 'gbg', 'jm'.")

        self.source_prefix = source_prefix
        self.entries = entries

    def __str__(self):
        return "\n".join(str(entry) for entry in self.entries)


class BaseCrawler:
    def __init__(self, config_key, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
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
        self.constants = self.load_config("constants")

        options = Options()
        if headless:
            options.add_argument("--headless")
        if no_images:
            options.add_argument("--blink-settings=imagesEnabled=false")
        if keep_window:
            options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_driver()

    @staticmethod
    def load_config(config_key):
        with open("config.json") as f:
            config = json.load(f)
        return config[config_key]

    def parse_table(self, table_object: WebElement, column_type: list) -> list[dict]:
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

            base_url = self.driver.current_url + self.constants['js_url']
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
                table_data.append(row_data)

        return table_data

    def fetch_main(self) -> list[dict]:
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
        return table[0]["article_id"]

    def last_page_number(self) -> int:
        """
        Fetch the last page number of the website
        :return: last page number
        """
        article_count = self.last_article_id()
        return article_count // self.config["articles_per_page"] + 1

    def fetch_article_list(self, page: int = 1) -> list[dict]:
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

    def element_from_xpath(self, element_xpath: str, timeout: int = 10) -> WebElement:
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


class GyeongbokgungCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("gyeongbokgung", headless, no_images, keep_window)


class ChanggyeonggungCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("changgyeonggung", headless, no_images, keep_window)


class ChangdeokgungCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("changdeokgung", headless, no_images, keep_window)


class JongmyoCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("jongmyo", headless, no_images, keep_window)


class DeoksugungEventsCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("deoksugung_events", headless, no_images, keep_window)


class DeoksugungNoticeCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("deoksugung_notice", headless, no_images, keep_window)


class RoyalTombsNoticeCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("royal_tombs_notice", headless, no_images, keep_window)


class RoyalTombsEventsCrawler(BaseCrawler):
    def __init__(self, headless: bool = True, no_images: bool = True, keep_window: bool = False) -> None:
        super().__init__("royal_tombs_events", headless, no_images, keep_window)


if __name__ == "__main__":
    Logger(debug=True)

    # article_url = input("URL: ")
    # article_url = "https://www.royalpalace.go.kr/content/board/view.asp?seq=970&page=&c1=&c2="

    with GyeongbokgungCrawler() as crawler:
        result = crawler.fetch_main()

    print(result)

    with open("result.json", "w") as file:
        file.write(json.dumps(result, ensure_ascii=False, indent=4))
