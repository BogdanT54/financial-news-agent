"""Formattere text pentru blocurile Bullish / Neutral / Bearish.

Port direct al celor 3 noduri 'All Bullish/Neutral/Bearish articles' din N8N
(JavaScript -> Python), păstrând layout-ul și emoji-urile.
"""
from typing import Any

SEPARATOR_THICK = "═" * 40
SEPARATOR_THIN = "─" * 40
UNAVAILABLE = {"", "Content_Unavailable", "ONLY AVAILABLE IN PAID PLANS"}


def _strength(confidence: float) -> str:
    if confidence >= 0.8:
        return "strong"
    if confidence >= 0.6:
        return "moderate"
    return "weak"


def _content_preview(article_content: str, limit: int = 2000) -> str | None:
    if not article_content or article_content in UNAVAILABLE:
        return None
    text = article_content[:limit].replace("\n", " ").strip()
    if len(article_content) > limit:
        text += "..."
    return text


def _format_article_block(
    article: dict[str, Any],
    index: int,
    emoji: str,
    label: str,
    score_order: list[str],
) -> str:
    title = article.get("title") or "No title"
    description = (article.get("description") or "").strip() or "—"
    source_name = article.get("source_name") or ""
    creator = article.get("creator") or ""
    link = article.get("link") or ""
    pub_date = (article.get("pubDate") or "")[:10]

    categories = article.get("categories") or []
    keywords = article.get("keywords") or []
    coins = article.get("coins") or []

    confidence = article.get("finbert_score") or 0.0
    confidence_level = article.get("confidence_level") or ""
    score_pos = article.get("score_positive") or 0.0
    score_neg = article.get("score_negative") or 0.0
    score_neu = article.get("score_neutral") or 0.0

    strength = _strength(confidence)
    content_preview = _content_preview(article.get("article_content", ""))

    source_line = source_name + (f" · {creator}" if creator else "")
    categories_str = ", ".join(categories) if isinstance(categories, list) else (categories or "")
    keywords_str = (
        ", ".join(keywords[:8]) if isinstance(keywords, list) else (keywords or "")
    )
    coins_str = ", ".join(coins) if coins else None

    lines = [
        f"{emoji} Article {index + 1} — {label} ({strength.upper()})",
        "",
        f"Title       : {title}",
        f"Source      : {source_line}",
        f"Published   : {pub_date}",
        f"Link        : {link}",
        "",
        f"Description : {description}",
        "",
        f"Content     : {content_preview}" if content_preview else "Content     : [Not available]",
        "",
        f"Categories  : {categories_str or '—'}",
        f"Keywords    : {keywords_str or '—'}",
    ]
    if coins_str:
        lines.append(f"Coins       : {coins_str}")
    lines.append("")
    lines.append("── FinBERT Scores ──────────────────")
    lines.append(f"Sentiment   : {label.capitalize()}")
    lines.append(f"Confidence  : {confidence * 100:.1f}%  [{confidence_level}]")

    score_values = {
        "positive": (score_pos, "Positive"),
        "negative": (score_neg, "Negative"),
        "neutral": (score_neu, "Neutral"),
    }
    for key in score_order:
        value, name = score_values[key]
        lines.append(f"  {name:<8}: {value * 100:.1f}%")

    return "\n".join(lines)


def _filter_by_sentiment(articles: list[dict[str, Any]], target_label: str, target_sentiment: str) -> list[dict[str, Any]]:
    filtered = [
        a
        for a in articles
        if str(a.get("finbert_label", "")).lower() == target_label
        or str(a.get("sentiment", "")).lower() == target_sentiment
    ]
    filtered.sort(key=lambda a: a.get("finbert_score", 0.0), reverse=True)
    return filtered


def format_bullish_block(articles: list[dict[str, Any]]) -> str:
    items = _filter_by_sentiment(articles, "positive", "bullish")
    if not items:
        return "No bullish articles found for this run."
    header = f"🟢 BULLISH ARTICLES ({len(items)} found)\n{SEPARATOR_THICK}\n"
    blocks = [
        _format_article_block(a, i, "🟢", "BULLISH", ["positive", "neutral", "negative"])
        for i, a in enumerate(items)
    ]
    return header + ("\n\n" + SEPARATOR_THIN + "\n\n").join(blocks)


def format_bearish_block(articles: list[dict[str, Any]]) -> str:
    items = _filter_by_sentiment(articles, "negative", "bearish")
    if not items:
        return "No bearish articles found for this run."
    header = f"🔴 BEARISH ARTICLES ({len(items)} found)\n{SEPARATOR_THICK}\n"
    blocks = [
        _format_article_block(a, i, "🔴", "BEARISH", ["negative", "neutral", "positive"])
        for i, a in enumerate(items)
    ]
    return header + ("\n\n" + SEPARATOR_THIN + "\n\n").join(blocks)


def format_neutral_block(articles: list[dict[str, Any]]) -> str:
    items = _filter_by_sentiment(articles, "neutral", "neutral")
    if not items:
        return "No neutral articles found for this run."
    header = f"⚪️ NEUTRAL ARTICLES ({len(items)} found)\n{SEPARATOR_THICK}\n"
    blocks = [
        _format_article_block(a, i, "⚪️", "NEUTRAL", ["neutral", "negative", "positive"])
        for i, a in enumerate(items)
    ]
    return header + ("\n\n" + SEPARATOR_THIN + "\n\n").join(blocks)
