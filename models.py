import re


class Article:
    def __init__(self, source_prefix: str, article_id: int, source_url: str, title: str, time: str, content: str):
        """
        Initialize a new article instance.

        :param source_prefix: Prefix of the source, Used to categorize the article's source.
        Must be one of: "cdg", "cgg", "dsg-e", "dsg-j", "dsg-n", "gbg", "jm" or "rt".
        :param article_id: Unique identifier for the article.
        :param source_url: URL of the article's original source.
        :param title: Title of the article.
        :param time: Timestamp of the article publication time, in the YYYY-MM-DD format.
        :param content: Main content of the article in markdown format.

        :raises ValueError: If the `source_prefix` is not one of the specified valid values.
        :raises ValueError: If the `article_id` is not an integer or less than 1.
        :raises ValueError: If the `time` is not in the YYYY-MM-DD format.
        """

        # Check for errors in the input
        if source_prefix and source_prefix not in ["cdg", "cgg", "dsg-e", "dsg-n", "gbg", "jm", "rt-n", "rt-e"]:
            raise ValueError(
                "Invalid source prefix. It must be one of: 'cdg', 'cgg', 'dsg-e', 'dsg-j', 'dsg-n', 'gbg', 'jm'.")

        if not article_id or not isinstance(article_id, int) or article_id < 1:
            raise ValueError(f"Invalid article ID. It must be a positive integer: {article_id}")

        if not time or not re.match(r"^\d{4}-\d{2}-\d{2}$", time):
            raise ValueError(f"Invalid time. It must be in the YYYY-MM-DD format: {time}")

        self.source_prefix = source_prefix
        self.article_id = article_id
        self.url = source_url
        self.title = title
        self.time = time
        self.content = content

    def __str__(self):
        return f"Article ID: {self.article_id}\n" \
               f"Source URL: {self.url}\n" \
               f"Title: {self.title}\n" \
               f"Time: {self.time}\n" \
               f"Content: {self.content}\n"


class PreviewItem:
    def __init__(self, article_id: int = None, title: str = None, url: str = None, time: str = None):
        """
        Initialize a new board entry item instance.

        :param article_id: Unique identifier for the article.
        :param title: Title of the article.
        :param url: URL of the article's original source.
        :param time: Timestamp of the article publication time, in the YYYY-MM-DD format.

        :raises ValueError: If the `article_id` is not an integer or less than 1.
        :raises ValueError: If the `time` is not in the YYYY-MM-DD format.
        """

        self.article_id = article_id
        self.title = title
        self.url = url
        self.time = time

    def set_title(self, title: str):
        self.title = title

    def set_url(self, url: str):
        self.url = url

    def set_time(self, time: str):
        self.time = time

    def set_article_id(self, article_id: int):
        self.article_id = article_id

    def is_valid(self) -> bool:
        """
        Validate the preview item.
        :return: True if the preview item is valid, and exists. False otherwise.
        """

        if not self.title or not self.url or not self.time:
            return False

        if not self.article_id or not isinstance(self.article_id, int) or self.article_id < 1:
            return False

        if re.match(r"^\d{4}-\d{2}-\d{2}$", self.time) is None:
            return False

        return True

    def __str__(self):
        return f"Article ID: {self.article_id}\n" \
               f"Title: {self.title}\n" \
               f"URL: {self.url}\n" \
               f"Time: {self.time}\n"

    def to_dict(self) -> dict:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "url": self.url,
            "time": self.time,
        }
