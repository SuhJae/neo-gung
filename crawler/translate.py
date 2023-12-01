import translators as ts
import concurrent.futures
from models import Article

from db import DatabaseManager
from crawler.log_manager import Logger, log
from typing import Optional


# for English: ts.translate_text(translator="papago", query_text=article.title, from_language="ko",
#                                                  to_language="en")


class ArticleTranslationScript:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.article_id_file = 'cache/mongo_article_id_list.txt'

    def fetch_article_ids(self) -> list:
        try:
            articles = self.db_manager.db.articles.find({}, {"_id": 1})
            article_ids = [str(article['_id']) for article in articles]

            with open(self.article_id_file, 'w') as file:
                file.write('\n'.join(article_ids))

            log.info("Article IDs fetched and saved to file.")
            return article_ids
        except Exception as e:
            log.error(f"Error fetching article IDs: {e}")
            return []

    @staticmethod
    def translate_article(article: Article) -> Optional[Article]:
        try:
            # uning papago translator to translate the article from Korean to English
            translated_title = ts.translate_text(translator="Mirai", query_text=article.title, from_language="ko",
                                                 to_language="ja")
            translated_content = ts.translate_text(translator="Mirai", query_text=article.content, from_language="ko",
                                                   to_language="ja")

            return Article(source_prefix=article.source_prefix, article_id=article.article_id, source_url=article.url,
                           title=translated_title,
                           time=article.time, content=translated_content, language='en')

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
                update_result = self.db_manager.add_language('ja', article, article_id)
                if update_result:
                    log.info(f"Article updated with English translation: {article_id}")
                else:
                    log.error(f"Failed to update article: {article_id}")
        except Exception as e:
            log.error(f"Error processing article {article_id}: {e}")

    def run(self, num_workers: int = 3) -> None:
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
