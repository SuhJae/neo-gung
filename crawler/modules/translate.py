import translators as ts
import concurrent.futures
from typing import Optional

from modules.models import Article
from modules.db import MongoDBClient
from modules.log_manager import Logger, log


# for English: ts.translate_text(translator="papago", query_text=article.title, from_language="ko",
#                                                  to_language="en")
# for Japanese: ts.translate_text(translator="papago", query_text=article.title, from_language="ko",
#                                                  to_language="ja")

class ArticleTranslationScript:
    def __init__(self):
        self.db_manager = MongoDBClient()
        self.article_id_file = 'cache/mongo_article_id_list.txt'

    def fetch_article_ids(self) -> list:
        try:
            articles = self.db_manager.db.articles.find({}, {"_id": 1})
            article_ids = [str(article['_id']) for article in articles]

            log.info("Article IDs fetched.")
            return article_ids
        except Exception as e:
            log.error(f"Error fetching article IDs: {e}")
            return []

    @staticmethod
    def translate_article(article: Article) -> Optional[Article]:
        try:
            # uning papago translator to translate the article from Korean to English
            translated_title = ts.translate_text(translator="papago", query_text=article.title, from_language="ko",
                                                 to_language="es")
            translated_content = ts.translate_text(translator="papago", query_text=article.content, from_language="ko",
                                                   to_language="es")

            return Article(source_prefix=article.source_prefix, article_id=article.article_id, source_url=article.url,
                           title=translated_title,
                           time=article.time, content=translated_content, language='es')

        except Exception as e:
            log.error(f"Error translating article: {e}")
            return None

    def process_article(self, article_id: str) -> None:
        try:
            # Fetch the article from the database using the ID
            article = self.db_manager.get_article_from_id(mongo_id=article_id)

            if not article:
                log.error(f"No article found with ID: {article_id}")
                return
            else:
                article = self.translate_article(article)
                update_result = self.db_manager.add_language('es', article, article_id)
                if update_result:
                    log.info(f"Article updated with translation: {article_id}")
                else:
                    log.error(f"Failed to update article: {article_id}")
        except Exception as e:
            log.error(f"Error processing article {article_id}: {e}")

    def run(self, num_workers: int = 1) -> None:
        # Fetch all article IDs
        article_ids = self.fetch_article_ids()

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Map the process_article function to each article ID
            executor.map(self.process_article, article_ids)


if __name__ == "__main__":
    Logger(debug=False)
    script = ArticleTranslationScript()
    script.run()
