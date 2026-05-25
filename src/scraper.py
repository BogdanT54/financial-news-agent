"""Scraping HTML + curățare + extracție conținut principal cu LLM."""
import re
import warnings
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import get_openrouter_llm

# Suprimă warning-urile inofensive de la with_structured_output (LangChain → Pydantic)
warnings.filterwarnings(
    "ignore",
    message=".*PydanticSerializationUnexpectedValue.*",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydantic.main",
)

DEFAULT_TIMEOUT = 30
MAX_CHARS = 9000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_article_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """GET pe link-ul articolului. Întoarce string gol dacă pică."""
    if not url:
        return ""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


_ENTITY_MAP = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
    "&mdash;": "—",
    "&ndash;": "–",
    "&ldquo;": '"',
    "&rdquo;": '"',
}


def clean_html(raw_html: str) -> str:
    """Port direct al nodului 'Clean html content' din N8N.

    - elimină <script>, <style>, <head>, comentarii, atribute inline
    - decode entități HTML
    - normalizează whitespace (max 2 newline-uri consecutive)
    - trunchiază la MAX_CHARS
    """
    if not raw_html:
        return ""

    html = raw_html.replace("\\n", "\n").replace("\\t", " ")

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "noscript", "iframe", "svg"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"<[^>]+>", " ", text)

    for entity, replacement in _ENTITY_MAP.items():
        text = text.replace(entity, replacement)
    text = re.sub(r"&#\d+;", " ", text)

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    text = "\n".join(line for line in text.split("\n") if len(line.strip()) > 3)

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + " [...]"

    return text


class _ArticleSchema(BaseModel):
    article_content: str = Field(
        description=(
            "Conținutul principal al articolului. Dacă nu sunt date "
            "disponibile, scrie literal: Content_Unavailable"
        )
    )


def extract_main_content(clean_text: str, model: Optional[str] = None) -> str:
    """Information Extractor (DeepSeek) — întoarce textul principal al articolului."""
    if not clean_text or clean_text.strip() == "":
        return "Content_Unavailable"

    settings = get_settings()
    llm = get_openrouter_llm(model or settings.MODEL_EXTRACTOR)
    structured = llm.with_structured_output(_ArticleSchema)

    prompt = (
        "Extrage conținutul principal al articolului din textul de mai jos. "
        "Ignoră meniuri, reclame, footer, sugestii de alte articole. "
        "Dacă nu există conținut util, scrie exact: Content_Unavailable.\n\n"
        f"{clean_text}"
    )

    try:
        result = structured.invoke(prompt)
        return result.article_content or "Content_Unavailable"
    except Exception:
        return "Content_Unavailable"
