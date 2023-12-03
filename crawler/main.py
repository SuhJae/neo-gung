from fastapi import FastAPI
from pydantic import BaseModel

from crawler.modules.db import MongoDBClient

class Article(BaseModel):
    source_prefix: str
    article_id: int
    source_url: str
    title: str
    time: str
    content: str
    language: str


app = FastAPI()
mongo_client = MongoDBClient()


@app.get("/api/v1/articles/{article_id}")
async def get_article(id: str):
