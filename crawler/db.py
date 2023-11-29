from datetime import datetime, timezone, timedelta
import json

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
        self.es = Elasticsearch(["http://localhost:9200"])

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

        with open("stopwords.txt", "r") as f:
            self.stopwords = f.read().splitlines()

    def setup_elasticsearch(self):
        with open("search_settings.json", "r") as f:
            settings = json.load(f)

        try:
            if self.es.indices.exists(index="articles"):
                # If the index exists, you can choose to delete and recreate it
                # or update its settings based on your requirements
                self.es.indices.delete(index="articles")
                log.info("Existing Elasticsearch index deleted")

            self.es.indices.create(index="articles", body=settings)
            log.info("Elasticsearch index created with Nori analyzer and synonym filter")
        except Exception as e:
            log.error(f"Error setting up Elasticsearch index: {e}")

    def insert_article(self, article: Article) -> bool:
        """
        Insert a new article into the database.
        :param article: Article object to insert.
        :return: True if the insertion was successful, False otherwise.
        """
        # extract the article's text from html for elastic search
        article_text = HTMLCleaner().html_to_text(article.content)

        # check if article text includes any of the stopwords
        # if so, return False
        for word in article_text.split():
            if word in self.stopwords:
                log.info(f"Article {article.article_id} contains stopwords")
                return True

        for word in article.title.split():
            if word in self.stopwords:
                log.info(f"Article {article.article_id} contains stopwords")
                return True

        # convert ISO (YYYY-MM-DD) date to mongoDB date format
        # set the time zone to GMT+9 (Seoul)
        entry_time = datetime.strptime(article.time, "%Y-%m-%d").replace(tzinfo=timezone.utc).astimezone(
            tz=timezone(timedelta(hours=9)))

        entry = {
            "tag": article.source_prefix,
            "o_id": article.article_id,
            "url": article.url,
            "title": article.title,
            "time": entry_time,
            "content": article.content,
        }

        # check if the article with same tag and o_id already exists and if so, overwrite it
        db_search = self.db.articles.find_one({"tag": article.source_prefix, "o_id": article.article_id})

        try:
            if db_search:
                entry_id = self.db.articles.update_one({"tag": article.source_prefix, "o_id": article.article_id},
                                                       {"$set": entry}).upserted_id
                log.info(f"Updated article: {article.article_id}")
            else:
                entry_id = self.db.articles.insert_one(entry).inserted_id
        except Exception as e:
            log.error(f"Error inserting article: {e}")
            return False

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
            log.error(f"Error indexing article: {e}")
            return False

    def search_articles(self, query: str):
        # Define the decay function for the date field
        # Setting decay to decrease relevance of articles older than now
        # No boost for articles older than 1 month
        decay_function = {
            "gauss": {
                "time": {
                    "origin": datetime.now().isoformat(),
                    "scale": "30d",  # Time scale of 1 month
                    "offset": "30d",  # No boost past 1 month
                    "decay": 0.5  # Adjust decay rate as needed
                }
            }
        }

        body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title", "text"],
                                    "analyzer": "korean",  # Explicitly specify the analyzer
                                    "fuzziness": "AUTO"
                                }
                            },
                            "should": [
                                {"match": {"title": {"query": query, "boost": 2, "analyzer": "korean"}}},
                                {"match": {"text": {"query": query, "analyzer": "korean"}}}
                            ]
                        }
                    },
                    "functions": [decay_function],
                    "boost_mode": "multiply"
                }
            }
        }
        return self.es.search(index="articles", body=body)


# Example usage
if __name__ == "__main__":
    db = DatabaseManager()
    db.search_articles("test")

    terms = input("Search articles: ")
    results = db.search_articles(terms)

    for result in results["hits"]["hits"]:
        print(f"Title: {result['_source']['title']}")
        print(f"Score: {result['_score']}")  # Score is calculated by Elasticsearch
        print(f"Text: {result['_source']['text']}")
        print()
