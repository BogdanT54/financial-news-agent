"""Setări încărcate din Colab Secrets (prioritar) sau .env (fallback)."""
import os
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


def load_colab_secrets(verbose: bool = False) -> dict:
    """Încarcă secretele din Google Colab Secrets în os.environ.
    Returnează un dict {key: 'loaded'|'already_set'|'missing'}.
    """
    status = {}
    try:
        from google.colab import userdata  # type: ignore
    except ImportError:
        return {k: "not_in_colab" for k in _COLAB_KEYS}

    for key in _COLAB_KEYS:
        if os.environ.get(key):
            status[key] = "already_set"
            continue
        try:
            value = userdata.get(key)
            if value:
                os.environ[key] = value
                status[key] = "loaded"
            else:
                status[key] = "missing"
        except Exception:
            status[key] = "missing"

    if verbose:
        for k, s in status.items():
            icon = "✅" if s in ("loaded", "already_set") else "❌"
            print(f"  {icon} {k:<25}: {s}")

    return status


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


def get_settings() -> Settings:
    """Creează Settings după ce încarcă Colab Secrets în os.environ."""
    load_colab_secrets()
    return Settings()
