from datetime import datetime, timezone, timedelta
from bson import ObjectId
from elasticsearch import Elasticsearch
from pymongo import MongoClient, DESCENDING
from typing import Optional

from modules.models import *
from modules.utils import strip_markdown
from modules.log_manager import log


class MongoDBClient:
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
        if article.language != "ko":
            log.warning(f"Initial article language is not Korean. Skipping: {article.language}")

        # convert ISO (YYYY-MM-DD) date to mongoDB date format
        entry_time = datetime.strptime(article.time, "%Y-%m-%d").replace(tzinfo=timezone.utc).astimezone(
            tz=timezone(timedelta(hours=9)))

        entry = {
            "tag": article.source_prefix,
            "o_id": article.article_id,
            "url": article.url,
            "time": entry_time,
            "title": {
                "ko": article.title,
            },
            "content": {
                "ko": article.content,
            }
        }

        try:
            # Using upsert to insert if not exists, else update
            result = self.db.articles.update_one(entry, {"$set": entry}, upsert=True)

            # Check if it was an insertion or an update
            if result.upserted_id:
                log.info(f"Inserted new article: {article.article_id}")
                entry_id = result.upserted_id
            else:
                log.info(f"Updated article: {article.article_id}")
                entry_id = result.matched_count

            # Continue with Elasticsearch insertion
            ElasticsearchClient().insert_article(article, entry_id)
        except Exception as e:
            # Broad catch for any other exceptions
            log.error(f"Error in article insertion/updation: {e}")
            return False
        return True

    def add_language(self, language: str, article: Article, mongo_id: str) -> bool:
        """
        Add a new language to the database.
        :param language: Language code to add.
        :param article: Article object to insert.
        :param mongo_id: MongoDB ID of the article.
        :return: True if the update was successful, False otherwise.
        """
        try:
            mongo_id = ObjectId(mongo_id)
            # Fetch the existing article from the database
            existing_entry = self.db.articles.find_one({"_id": mongo_id})

            if not existing_entry:
                log.error(f"No article found with ID: {mongo_id}")
                return False

            # Update the title and content with the new language
            # This will overwrite the existing title and content for specified language
            updated_entry = existing_entry
            updated_entry["title"][language] = article.title
            updated_entry["content"][language] = article.content

            # Save the updated entry back to the database
            result = self.db.articles.update_one({"_id": mongo_id}, {"$set": updated_entry})

            if result.matched_count == 0:
                log.error(f"Error while updating article: {mongo_id} ({result.raw_result})")
                return False

            log.info(f"Added language '{language}' to article: {mongo_id}")
        except Exception as e:
            log.error(f"Error in adding language to article: {e}")
            return False
        return True

    def get_article_from_id(self, mongo_id: str, language: str = 'ko') -> Optional[Article]:
        try:
            # Convert string ID to ObjectId
            object_id = ObjectId(mongo_id)
            article = self.db.articles.find_one({"_id": object_id})
            if not article:
                log.error(f"No article found with ID: {mongo_id}")
                return None

            time_formatted = article['time'].strftime('%Y-%m-%d')

            return Article(article['tag'], article['o_id'], article['url'], article['title'][language],
                           time_formatted, article['content'][language])
        except Exception as e:
            log.error(f"Error fetching article from ID: {e}")
            return None

    def get_latest_article(self, language: str = 'ko', cursor_id: str = None, limit: int = 20) -> list[Article]:
        query = {}

        if cursor_id:
            starting_article = self.db.articles.find_one({"_id": ObjectId(cursor_id)}, {"time": 1})
            if starting_article:
                query = {"time": {"$lt": starting_article["time"]}}

        articles = self.db.articles.find(query).sort("time", DESCENDING).limit(limit)
        article_list = []

        for article in articles:
            time_formatted = article['time'].strftime('%Y-%m-%d')
            article_list.append(Article(article['tag'], article['o_id'], article['url'], article['title'][language],
                                        time_formatted, article['content'][language], language))

        return article_list


class ElasticsearchClient:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")
        try:
            self.es.ping()
            log.info("Connected to Elasticsearch server")
        except Exception as e:
            log.error(f"Failed connecting to Elasticsearch server: {e}")
            exit(1)

    def setup_index(self) -> None:
        # reset the index
        for language in Article.valid_languages:
            index_name = f'articles_{language}'
            if self.es.indices.exists(index=index_name):
                self.es.indices.delete(index=index_name)
                print(f"Deleted index: {index_name}")

        # Define the analyzer name based on the language
        analyzer_mapping = {
            "ko": "korean",
            "en": "english",
            "ja": "japanese",
            "zh": "chinese",
            "es": "spanish"
        }

        for language in Article.valid_languages:
            analyzer_name = analyzer_mapping[language]
            print(f"Creating index for language: {language} with analyzer: {analyzer_name}")

            settings = {
                "settings": {
                    "index": {
                        "analysis": {
                            "analyzer": {
                                "korean": {
                                    "type": "custom",
                                    "tokenizer": "nori_tokenizer",
                                    "filter": ["nori_readingform"]
                                },
                                "english": {
                                    "type": "standard"
                                },
                                "japanese": {
                                    "type": "custom",
                                    "tokenizer": "kuromoji_tokenizer",
                                    "filter": [
                                        "kuromoji_baseform",
                                        "kuromoji_part_of_speech",
                                        "cjk_width",
                                        "ja_stop"
                                    ]
                                },
                                "chinese": {
                                    "type": "custom",
                                    "tokenizer": "smartcn_tokenizer",  # or "ik_smart" for IK analyzer
                                    "filter": ["cjk_width", "stop"]
                                },
                                "spanish": {
                                    "type": "standard"  # or use a custom Spanish analyzer
                                }
                            },
                            "tokenizer": {
                                "nori_tokenizer": {
                                    "type": "nori_tokenizer",
                                    "decompound_mode": "mixed",
                                },
                                "kuromoji_tokenizer": {
                                    "type": "kuromoji_tokenizer"
                                },
                            },
                            "filter": {
                                "ja_stop": {
                                    "type": "stop",
                                    "stopwords": "_japanese_"
                                }
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": analyzer_name
                        },
                        "text": {
                            "type": "text",
                            "analyzer": analyzer_name
                        },
                        "suggest": {
                            "type": "completion",
                            "analyzer": analyzer_name,
                            "search_analyzer": analyzer_name,
                            "preserve_separators": True,
                            "preserve_position_increments": True,
                            "max_input_length": 50
                        }
                    }
                }
            }
            index_name = f'articles_{language}'
            self.es.indices.create(index=index_name, body=settings)

    def insert_article(self, article: Article, entry_id: str, language='ko'):
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
        index_name = f'articles_{language}'
        # Insert the article into Elasticsearch
        self.es.index(index=index_name, body=es_entry, id=entry_id)

    def search_articles(self, query: str, language='ko', cursor: int = 0, limit: int = 20):
        index_name = f'articles_{language}'
        response = self.es.search(index=index_name, body={
            "from": cursor,  # Starting point for the results
            "size": limit,  # Number of search hits to return
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

    def autocomplete(self, query: str, language='ko') -> list[str]:
        index_name = f'articles_{language}'
        response = self.es.search(index=index_name, body={
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
