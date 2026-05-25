"""Preluare știri din NewsData.io (5 surse, în paralel)."""
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

from .config import get_settings

BASE_LATEST = "https://newsdata.io/api/1/latest"
BASE_CRYPTO = "https://newsdata.io/api/1/crypto"

DEFAULT_TIMEOUT = 30


def _get(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_politics(api_key: str | None = None) -> dict[str, Any]:
    key = api_key or get_settings().NEWSDATA_API_KEY
    return _get(BASE_LATEST, {
        "apikey": key,
        "q": "Politics",
        "country": "us,ro,de",
        "language": "en,ro",
        "category": "business,politics,world,technology",
    })


def fetch_economics(api_key: str | None = None) -> dict[str, Any]:
    key = api_key or get_settings().NEWSDATA_API_KEY
    return _get(BASE_LATEST, {
        "apikey": key,
        "q": "eCONOMICS",
        "country": "us,ro,de",
        "language": "en,ro",
        "category": "business,politics,world,technology",
    })


def fetch_bitcoin(api_key: str | None = None) -> dict[str, Any]:
    key = api_key or get_settings().NEWSDATA_API_KEY
    return _get(BASE_CRYPTO, {
        "apikey": key,
        "q": "Bitcoin",
        "coin": "btc",
        "language": "en,ro",
    })


def fetch_ethereum(api_key: str | None = None) -> dict[str, Any]:
    key = api_key or get_settings().NEWSDATA_API_KEY
    return _get(BASE_CRYPTO, {
        "apikey": key,
        "q": "Ethereum",
        "coin": "eth",
        "language": "en,ro",
    })


def fetch_solana_ecosystem(api_key: str | None = None) -> dict[str, Any]:
    key = api_key or get_settings().NEWSDATA_API_KEY
    return _get(BASE_CRYPTO, {
        "apikey": key,
        "q": "Solana",
        "coin": "btc,sol,jup,bonk,eth",
        "language": "en,ro",
    })


FETCHERS = [
    ("politics", fetch_politics),
    ("economics", fetch_economics),
    ("bitcoin", fetch_bitcoin),
    ("ethereum", fetch_ethereum),
    ("solana", fetch_solana_ecosystem),
]


def fetch_all_news(api_key: str | None = None) -> dict[str, dict[str, Any]]:
    """Rulează toate cele 5 fetchere în paralel."""
    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn, api_key): name for name, fn in FETCHERS}
        for future in futures:
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = {"error": str(exc), "results": []}
    return results


def merge_news_sources(responses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Reproduce Merge + Split Out din N8N: extrage `results[]` din fiecare răspuns."""
    merged: list[dict[str, Any]] = []
    for source_name, payload in responses.items():
        results = payload.get("results") or []
        for item in results:
            item.setdefault("_source_bucket", source_name)
            merged.append(item)
    return merged
