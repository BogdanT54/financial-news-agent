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
