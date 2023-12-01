from datetime import datetime, timezone, timedelta

from elasticsearch import Elasticsearch
from pymongo import MongoClient
from models import *
from utils import strip_markdown
from log_manager import log


class DatabaseManager:
    def __init__(self):
        # mongoDB
        self.client = MongoClient("localhost", 27017)
        self.db = self.client["articles"]

        # ping the server to check if it's available
        try:
            self.client.admin.command('ismaster')
            log.info("Connected to MongoDB server")
        except Exception as e:
            log.error(f"Error connecting to MongoDB server: {e}")
            exit(1)

    def insert_article(self, article: Article) -> bool:
        """
        Insert a new article into the database.
        :param article: Article object to insert.
        :return: True if the insertion was successful, False otherwise.
        """
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

        ElasticsearchClient().insert_article(article, entry_id)


class ElasticsearchClient:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")

        try:
            self.es.ping()
            log.info("Connected to Elasticsearch server")
        except Exception as e:
            log.error(f"Error connecting to Elasticsearch server: {e}")
            exit(1)

    def setup_index(self):
        # Define the settings for the Nori analyzer
        settings = {
            "settings": {
                "index": {
                    "analysis": {
                        "analyzer": {
                            "korean": {
                                "type": "custom",
                                "tokenizer": "nori_tokenizer",
                                "filter": ["nori_readingform"]
                            }
                        },
                        "tokenizer": {
                            "nori_tokenizer": {
                                "type": "nori_tokenizer",
                                "decompound_mode": "mixed",
                                # "user_dictionary": "userdict_ko.txt"
                            }
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "korean"
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "korean"
                    },
                    "suggest": {  # Correctly place the suggest field within the properties
                        "type": "completion",
                        "analyzer": "korean",
                        "search_analyzer": "korean",  # Use the Simple analyzer for searching
                        "preserve_separators": True,
                        "preserve_position_increments": True,
                        "max_input_length": 50
                    }
                }
            }
        }
        self.es.indices.create(index='articles', body=settings)

    def insert_article(self, article: Article, entry_id: str):
        # Prepare the entry for Elasticsearch
        entry_time = datetime.strptime(article.time, "%Y-%m-%d")
        article_text = strip_markdown(article.content)

        es_entry = {
            "tag": article.source_prefix,
            "o_id": article.article_id,
            "title": article.title,
            "time": entry_time,
            "text": article_text,
            "suggest": article.title
        }
        # Insert the article into Elasticsearch
        self.es.index(index="articles", body=es_entry, id=entry_id)

    def search_articles(self, query: str):
        # Perform a search in Elasticsearch using the Nori analyzer for both Title and Text fields
        # Title matches are boosted, and recent articles are given a higher score
        response = self.es.search(index="articles", body={
            "query": {
                "function_score": {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "text"],  # Boost title matches
                            "fuzziness": "AUTO"
                        }
                    },
                    "functions": [
                        {
                            "gauss": {
                                "time": {
                                    "origin": "now",
                                    "scale": "60d",
                                    "offset": "60d",
                                    "decay": 0.5
                                }
                            }
                        }
                    ],
                    "score_mode": "multiply"  # Combine the scores from the query and the function
                }
            },
        })
        return response

    def autocomplete(self, query: str):
        response = self.es.search(index="articles", body={
            "suggest": {
                "article_suggest": {
                    "prefix": query,
                    "completion": {
                        "field": "suggest"
                    }
                }
            }
        })

        # Extracting suggestions
        suggestions = response.get('suggest', {}).get('article_suggest', [])[0].get('options', [])
        return [suggestion['text'] for suggestion in suggestions]


if __name__ == "__main__":
    elastic = ElasticsearchClient()
    # elastic.setup_index()

    while True:
        terms = input("Search articles: ")
        if terms == "":
            break

        # Get autocomplete suggestions
        print(elastic.autocomplete(terms))

        # Search for articles
        hits = elastic.search_articles(terms)
        for hit in hits['hits']['hits']:
            print(f"Title: {hit['_source']['title']}")
            # print(f"Time: {hit['_source']['time']}")
            print(f"Score: {hit['_score']}")
            print("")

        print("=====================================")
        print(f"Total hits: {hits['hits']['total']['value']} articles")
        print(f"Took: {hits['took']}ms")
