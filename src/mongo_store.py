"""MongoDB: istoric articole financiare + memorie chat pentru agenți."""
from typing import Any, Optional

from langchain_mongodb import MongoDBChatMessageHistory
from pymongo import MongoClient

from .config import get_settings

_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.MONGO_URI)
    return _client


def insert_articles(articles: list[dict[str, Any]]) -> int:
    """Inserează articolele în collection-ul `fin_news_history`.

    Aliniat cu nodul 'Insert financial articles' din N8N care folosea
    proiecția pe metadata.* — aici stocăm tot dict-ul agregat.
    """
    if not articles:
        return 0
    settings = get_settings()
    collection = get_client()[settings.MONGO_DB][settings.MONGO_ARTICLES_COLLECTION]
    result = collection.insert_many(articles)
    return len(result.inserted_ids)


def count_articles() -> int:
    """Numărul total de articole din colecție."""
    settings = get_settings()
    return get_client()[settings.MONGO_DB][settings.MONGO_ARTICLES_COLLECTION].count_documents({})


def get_recent_articles(n: int = 10, fields: Optional[dict] = None) -> list[dict]:
    """Returnează ultimele N articole inserate (sortate descendent după _id)."""
    settings = get_settings()
    col = get_client()[settings.MONGO_DB][settings.MONGO_ARTICLES_COLLECTION]
    projection = fields or {
        "_id": 0, "title": 1, "sentiment": 1, "confidence_level": 1,
        "finbert_score": 1, "pubDate": 1, "source_name": 1, "link": 1,
    }
    return list(col.find({}, projection).sort("_id", -1).limit(n))


def get_chat_memory(session_id: str) -> MongoDBChatMessageHistory:
    """Întoarce memoria conversațională indexată după session_id.

    Echivalent cu 'MongoDB Chat Memory' din N8N (collection `Chat_history`,
    sessionKey = workflow id).
    """
    settings = get_settings()
    return MongoDBChatMessageHistory(
        connection_string=settings.MONGO_URI,
        session_id=session_id,
        database_name=settings.MONGO_DB,
        collection_name=settings.MONGO_CHAT_COLLECTION,
    )
