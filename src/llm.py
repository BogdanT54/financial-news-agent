"""Factory pentru chat model pe OpenRouter (compatibil OpenAI API)."""
from typing import Optional

from langchain_openai import ChatOpenAI

from .config import get_settings


def get_openrouter_llm(
    model: str,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """Întoarce un ChatOpenAI configurat să folosească OpenRouter."""
    settings = get_settings()
    kwargs = dict(
        model=model,
        temperature=temperature,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)
