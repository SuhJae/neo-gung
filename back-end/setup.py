# This file is used to setup on the initial run of the back-end
from pymongo import DESCENDING

from modules.db import MongoDBClient, ElasticsearchClient
from modules.models import Article
from tqdm import tqdm

es = ElasticsearchClient()
mongo = MongoDBClient()

# Setup MongoDB indexes
print("Setting up MongoDB indexes...")
# check if index exists
if "articles" in mongo.db.list_collection_names() and "time_-1" not in mongo.db.articles.index_information():
    mongo.db.articles.create_index([("time", DESCENDING)])
    print("MongoDB index created.")
else:
    print("MongoDB index already exists.")

# Setup Elasticsearch index
es.setup_index()
print("Elasticsearch index created.")


def index_language(lang: str) -> None:
    articles = list(mongo.db.articles.find({}))  # Convert cursor to list
    total = len(articles)  # Get the total number of articles

    for i, article in enumerate(tqdm(articles, desc=f"Indexing articles for language {lang}",
                                     colour='WHITE', unit='articles', ascii=True)):
        article_id = article['_id']
        article = mongo.get_article_from_id(mongo_id=article_id, language=lang)
        es.insert_article(article=article, entry_id=article_id, language=lang)


for language in Article.valid_languages:
    index_language(lang=language)
