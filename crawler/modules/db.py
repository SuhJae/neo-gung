from datetime import datetime, timezone, timedelta
from bson import ObjectId
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from typing import Optional

from crawler.modules.models import *
from crawler.modules.utils import strip_markdown
from crawler.modules.log_manager import log


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

    def get_article_from_id(self, mongo_id: str) -> Optional[Article]:
        try:
            # Convert string ID to ObjectId
            object_id = ObjectId(mongo_id)
            article = self.db.articles.find_one({"_id": object_id})
            if not article:
                log.error(f"No article found with ID: {mongo_id}")
                return None

            time_formatted = article['time'].strftime('%Y-%m-%d')

            return Article(article['tag'], article['o_id'], article['url'], article['title']['ko'],
                           time_formatted, article['content']['ko'])
        except Exception as e:
            log.error(f"Error fetching article from ID: {e}")
            return None


class ElasticsearchClient:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")
        try:
            self.es.ping()
            log.info("Connected to Elasticsearch server")
        except Exception as e:
            log.error(f"Failed connecting to Elasticsearch server: {e}")
            exit(1)

    def setup_index(self, language: str = 'ko') -> None:
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
                            },
                            "english": {
                                "type": "standard"
                            }
                        },
                        "tokenizer": {
                            "nori_tokenizer": {
                                "type": "nori_tokenizer",
                                "decompound_mode": "mixed",
                            }
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "korean" if language == 'ko' else "english"
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "korean" if language == 'ko' else "english"
                    },
                    "suggest": {
                        "type": "completion",
                        "analyzer": "korean" if language == 'ko' else "english",
                        "search_analyzer": "korean" if language == 'ko' else "english",
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

    def search_articles(self, query: str, language='ko') -> Elasticsearch.search:
        index_name = f'articles_{language}'
        response = self.es.search(index=index_name, body={
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

    def autocomplete(self, query: str, language='ko'):
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
        hits = elastic.search_articles(terms, language='en')
        for hit in hits['hits']['hits']:
            print(f"Title: {hit['_source']['title']}")
            # print(f"Time: {hit['_source']['time']}")
            print(f"Score: {hit['_score']}")
            print("")

        print("=====================================")
        print(f"Total hits: {hits['hits']['total']['value']} articles")
        print(f"Took: {hits['took']}ms")
