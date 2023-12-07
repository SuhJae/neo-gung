from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from modules.db import MongoDBClient, ElasticsearchClient
from modules.models import Article


class ArticleRequest(BaseModel):
    article_id: str
    language: str


class SearchRequest(BaseModel):
    query: str
    language: str
    cursor: int


class AutoCompleteRequest(BaseModel):
    query: str
    language: str


class FeedRequest(BaseModel):
    language: str
    cursor: Optional[str]


class LanguageRequest(BaseModel):
    language: str


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

mongo_client = MongoDBClient()
es_client = ElasticsearchClient()

ui_language = {}
# read languages from config file
for lang in Article.valid_languages:
    with open(f"assets/lang/{lang}.json", "r", encoding="utf-8") as f:
        ui_language[lang] = f.read()


async def validate_language(language: str) -> Optional[HTTPException]:
    """
    Validates the language parameter in the request as a dependency.
    :param language: The language code to validate.
    :raise HTTPException: If the language is invalid.
    """
    if language not in Article.valid_languages:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid language: {language}")
    else:
        return None


@app.get("/")
def read_root():
    return FileResponse('static/index.html')


@app.get("/api/v1/search/")
async def search(request_data: SearchRequest):
    validation = await validate_language(request_data.language)
    if validation:
        return validation

    query = es_client.search_articles(query=request_data.query, language=request_data.language,
                                      cursor=request_data.cursor, limit=20)

    # From the elastic search raw response, we only need the mongoDB id of the article

    id_list = []

    for hit in query['hits']['hits']:
        id_list.append(hit['_id'])

    return {"total": query['hits']['total']['value'], "articles": id_list}, status.HTTP_200_OK


@app.get("/api/v1/feed/")
async def feed(language: str, cursor: Optional[str] = None):
    validation = await validate_language(language)
    if validation:
        return validation

    return mongo_client.get_latest_article(language, cursor, 20), status.HTTP_200_OK


@app.get("/api/v1/auto-complete/")
async def auto_complete(request_data: AutoCompleteRequest):
    validation = await validate_language(request_data.language)
    if validation:
        return validation

    query = es_client.autocomplete(query=request_data.query, language=request_data.language)
    return {"suggest": query}, status.HTTP_200_OK


@app.get("/api/v1/articles/")
async def get_article(request_data: ArticleRequest):
    validation = await validate_language(request_data.language)
    if validation:
        return validation

    document = mongo_client.get_article_from_id(request_data.article_id, request_data.language)

    if document:
        return document, status.HTTP_200_OK
    else:
        return {"message": f"No article found with ID: {request_data.article_id}"}, status.HTTP_404_NOT_FOUND


@app.get("/api/v1/articles/count/")
async def get_article_count():
    return mongo_client.get_article_count(), status.HTTP_200_OK


@app.get("/api/v1/languages/")
async def get_languages(language: str):
    validation = await validate_language(language)
    if validation:
        return validation

    return ui_language[language], status.HTTP_200_OK
