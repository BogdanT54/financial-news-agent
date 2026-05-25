"""Clasificare sentiment financiar cu FinBERT prin HuggingFace Inference API."""
import time
from typing import Any

import requests

from .config import get_settings

FINBERT_URL = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
MAX_INPUT_CHARS = 1200
DEFAULT_TIMEOUT = 60


def _build_input(title: str, description: str, content: str) -> str:
    """Identic cu N8N: title + '. ' + description + '. ' + content, slice 1200."""
    text = f"{title or ''}. {description or ''}. {content or ''}"
    return text[:MAX_INPUT_CHARS]


def classify_sentiment(
    title: str,
    description: str,
    content: str,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Întoarce lista [{label, score}, ...] de la FinBERT (positive/negative/neutral)."""
    hf_token = token or get_settings().HF_API_TOKEN
    payload = {"inputs": _build_input(title, description, content)}
    headers = {"Authorization": f"Bearer {hf_token}"}

    response = requests.post(FINBERT_URL, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, list) and data and isinstance(data[0], list):
        return data[0]
    if isinstance(data, list):
        return data
    return []


def classify_batch(
    items: list[dict[str, str]],
    batch_size: int = 5,
    batch_interval_sec: float = 1.5,
) -> list[list[dict[str, Any]]]:
    """Reproduce batching-ul din N8N (5 / 1.5s)."""
    results: list[list[dict[str, Any]]] = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        for item in batch:
            try:
                results.append(
                    classify_sentiment(
                        item.get("title", ""),
                        item.get("description", ""),
                        item.get("content", ""),
                    )
                )
            except Exception:
                results.append([])
        if i + batch_size < len(items):
            time.sleep(batch_interval_sec)
    return results
