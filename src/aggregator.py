"""Construiește înregistrarea finală per articol (port al nodului 'Aggregate data')."""
from datetime import datetime, timezone
from typing import Any


PIPELINE_VERSION = "2.0"


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return [value]


def _confidence_level(diff: float) -> str:
    if diff > 0.5:
        return "High"
    if diff > 0.25:
        return "Medium"
    return "Low"


def _map_sentiment(label: str) -> str:
    label_lower = (label or "").lower()
    if "positive" in label_lower:
        return "Bullish"
    if "negative" in label_lower:
        return "Bearish"
    return "Neutral"


def build_article_record(
    raw: dict[str, Any],
    extracted_content: str,
    finbert_predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compune dict-ul final cu toate metadatele articolului + scoruri FinBERT.

    Identic cu output-ul nodului 'Aggregate data' din N8N.
    """
    predictions = finbert_predictions or []
    sorted_preds = sorted(predictions, key=lambda p: p.get("score", 0), reverse=True)
    best = sorted_preds[0] if sorted_preds else {"label": "neutral", "score": 0.0}

    score_map = {str(p.get("label", "")).lower(): p.get("score", 0.0) for p in predictions}
    positive = score_map.get("positive", 0.0)
    negative = score_map.get("negative", 0.0)
    neutral = score_map.get("neutral", 0.0)

    sentiment = _map_sentiment(best.get("label", ""))
    second_score = sorted_preds[1].get("score", 0.0) if len(sorted_preds) > 1 else 0.0
    confidence_diff = best.get("score", 0.0) - second_score
    confidence_level = _confidence_level(confidence_diff)

    coins = list({c for c in _ensure_list(raw.get("coin")) if c})
    categories = _ensure_list(raw.get("category"))
    keywords = _ensure_list(raw.get("keywords"))
    countries = _ensure_list(raw.get("country"))
    creator_list = _ensure_list(raw.get("creator"))

    return {
        # — Identificare —
        "article_id": raw.get("article_id", ""),
        "link": raw.get("link", ""),
        "duplicate": raw.get("duplicate", False),

        # — Conținut —
        "title": raw.get("title", ""),
        "description": raw.get("description", ""),
        "article_content": extracted_content or raw.get("content", "") or "",

        # — Clasificare —
        "categories": categories,
        "keywords": keywords,
        "datatype": raw.get("datatype", "news"),
        "language": raw.get("language", "english"),
        "country": countries,

        # — Sursă —
        "source_id": raw.get("source_id", ""),
        "source_name": raw.get("source_name", ""),
        "source_url": raw.get("source_url", ""),
        "source_icon": raw.get("source_icon", ""),
        "source_priority": raw.get("source_priority"),
        "creator": creator_list[0] if creator_list else "",

        # — Timp —
        "pubDate": raw.get("pubDate", ""),
        "pubDateTZ": raw.get("pubDateTZ", "UTC"),
        "fetched_at": raw.get("fetched_at", ""),

        # — Media —
        "image_url": raw.get("image_url", ""),
        "video_url": raw.get("video_url"),

        # — Crypto —
        "coins": coins,
        "has_crypto": len(coins) > 0,

        # — FinBERT —
        "sentiment": sentiment,
        "confidence_level": confidence_level,
        "finbert_label": best.get("label", ""),
        "finbert_score": round(float(best.get("score", 0.0)), 6),
        "score_positive": round(float(positive), 6),
        "score_negative": round(float(negative), 6),
        "score_neutral": round(float(neutral), 6),

        # — Metadata pipeline —
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
    }
