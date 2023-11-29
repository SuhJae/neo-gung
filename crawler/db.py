import datetime

from elasticsearch import Elasticsearch
from pymongo import MongoClient
from models import *
from utils import HTMLCleaner
from log_manager import log


class DatabaseManager:
    def __init__(self):
        # mongoDB
        self.client = MongoClient("localhost", 27017)
        self.db = self.client["articles"]

        # elasticsearch
        self.es = Elasticsearch(["localhost:9200"])

        # ping the server to check if it's available
        try:
            self.client.admin.command('ismaster')
            log.info("Connected to MongoDB server")
        except Exception as e:
            log.error(f"Error connecting to MongoDB server: {e}")
            exit(1)

        try:
            self.es.ping()
            log.info("Connected to Elasticsearch server")
        except Exception as e:
            log.error(f"Error connecting to Elasticsearch server: {e}")
            exit(1)

    def insert_article(self, article: Article) -> bool:
        """
        Insert a new article into the database.
        :param article: Article object to insert.
        :return: True if the insertion was successful, False otherwise.
        """
        # convert ISO (YYYY-MM-DD) date to mongoDB date format
        # set the time zone to GMT+9 (Seoul)
        entry_time = datetime.datetime.strptime(article.time, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        entry_time = entry_time.astimezone(datetime.timezone(datetime.timedelta(hours=9)))

        entry = {
            "tag": article.source_prefix,
            "o_id": article.article_id,
            "url": article.url,
            "title": article.title,
            "time": entry_time,
            "content": article.content,
        }

        try:
            entry_id = self.db.articles.insert_one(entry).inserted_id
        except Exception as e:
            print(e)
            return False

        # extract the article's text from html for elastic search
        article_text = HTMLCleaner().html_to_text(article.content)

        es_entry = {
            "tag": article.source_prefix,
            "o_id": article.article_id,
            "title": article.title,
            "time": entry_time,
            "text": article_text  # Using cleaned text for Elasticsearch
        }
        try:
            self.es.index(index="articles", id=entry_id, document=es_entry)
            return True
        except Exception as e:
            print(e)
            return False

    def search_articles(self, query: str):
        # Implement search logic here
        # Example basic search queryx
        body = {
            "query": {
                "match": {
                    "text": query
                }
            }
        }
        return self.es.search(index="articles", body=body)
