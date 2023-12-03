from crawler.modules.db import MongoDBClient
from crawler.modules.log_manager import Logger, log

Logger(debug=False)

# get all article from article collection and itterate over them
# check the "title" field and "content" object has 5 elements in it

db_manager = MongoDBClient()
articles = db_manager.db.articles.find({})


for article in articles:
    log.info(f"Checking article: {article['_id']}")
    if len(article['title']) != 5:
        log.error(f"Article ID: {article['_id']}")
        log.error(f"Missing some translation: {article['title']}")
    if len(article['content']) != 5:
        log.error(f"Article ID: {article['_id']}")
        log.error(f"Missing some translation: {article['content']}")

log.info(f"Done checking articles.")
