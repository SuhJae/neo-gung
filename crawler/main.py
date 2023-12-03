from fastapi import FastAPI
from fastapi import status
from pydantic import BaseModel

from modules.db import MongoDBClient
from modules.models import Article


class ArticleRequest(BaseModel):
    article_id: str
    language: str


app = FastAPI()
mongo_client = MongoDBClient()


@app.get("/api/v1/articles/")
async def get_article(request_data: ArticleRequest):
    if request_data.language not in Article.valid_languages:
        return {"message": f"Invalid language: {request_data.language}"}, status.HTTP_400_BAD_REQUEST

    document = mongo_client.get_article_from_id(request_data.article_id, request_data.language)

    if document:
        return document, status.HTTP_200_OK
    else:
        return {"message": f"No article found with ID: {request_data.article_id}"}, status.HTTP_404_NOT_FOUND


