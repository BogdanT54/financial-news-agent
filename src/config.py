"""Setări încărcate din Colab Secrets (prioritar) sau .env (fallback)."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_COLAB_KEYS = [
    "NEWSDATA_API_KEY",
    "HF_API_TOKEN",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
    "MONGO_URI",
    "MONGO_DB",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def _load_colab_secrets() -> None:
    """Încearcă să încarce secretele din Google Colab Secrets în os.environ."""
    try:
        from google.colab import userdata  # type: ignore
    except ImportError:
        return  # Nu suntem în Colab

    for key in _COLAB_KEYS:
        if os.environ.get(key):
            continue  # deja setat (din .env sau manual)
        try:
            value = userdata.get(key)
            if value:
                os.environ[key] = value
        except Exception:
            pass  # secretul nu există în Colab Secrets — ignoră


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    NEWSDATA_API_KEY: str = ""
    HF_API_TOKEN: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "fin-news-documents"

    MONGO_URI: str = ""
    MONGO_DB: str = "fin-news-db"
    MONGO_ARTICLES_COLLECTION: str = "fin_news_history"
    MONGO_CHAT_COLLECTION: str = "Chat_history"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    MODEL_SUB_AGENT: str = "deepseek/deepseek-v4-flash"
    MODEL_MAIN_AGENT: str = "x-ai/grok-4.3"
    MODEL_EXTRACTOR: str = "deepseek/deepseek-v4-flash"

    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    DRY_RUN: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_colab_secrets()
    return Settings()
