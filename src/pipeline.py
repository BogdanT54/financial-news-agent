"""Orchestratorul pipeline-ului zilnic.

Reproduce flow-ul 'Daily news agent' din N8N end-to-end:
fetch -> scrape -> clean -> extract -> FinBERT -> aggregate ->
persist (Pinecone + Mongo) -> format Bullish/Neutral/Bearish ->
3 sub-agenți -> main agent -> Telegram (text + audio TTS).
"""
from typing import Any, Optional

from tqdm import tqdm

from . import (
    aggregator,
    finbert,
    formatters,
    news_fetcher,
    scraper,
    tts,
    telegram_io,
    vectorstore,
    mongo_store,
    agents,
)
from .config import get_settings


def _process_article(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Pipeline pentru un singur articol: scrape -> clean -> extract -> FinBERT -> aggregate."""
    link = raw.get("link", "")

    raw_html = scraper.fetch_article_html(link)
    clean_text = scraper.clean_html(raw_html) if raw_html else ""

    if clean_text:
        article_content = scraper.extract_main_content(clean_text)
    else:
        article_content = "Content_Unavailable"

    try:
        predictions = finbert.classify_sentiment(
            raw.get("title", ""),
            raw.get("description", ""),
            article_content if article_content != "Content_Unavailable" else "",
        )
    except Exception:
        predictions = []

    if not predictions:
        return None

    return aggregator.build_article_record(raw, article_content, predictions)


def run_daily_pipeline(
    max_articles: Optional[int] = None,
    dry_run: Optional[bool] = None,
    send_telegram: Optional[bool] = None,
    persist: Optional[bool] = None,
) -> dict[str, Any]:
    """Rulează tot pipeline-ul. Întoarce raportul + audio + stats.

    Args:
        max_articles: limită articole pentru demo rapid (default: fără limită)
        dry_run: dacă True, suprascrie send_telegram=False și persist=False
        send_telegram: trimite raportul + audio pe Telegram
        persist: scrie articolele în Pinecone + MongoDB
    """
    settings = get_settings()
    effective_dry_run = settings.DRY_RUN if dry_run is None else dry_run
    effective_send = (not effective_dry_run) if send_telegram is None else send_telegram
    effective_persist = (not effective_dry_run) if persist is None else persist

    print("→ Fetching news from NewsData.io (5 sources in parallel)...")
    responses = news_fetcher.fetch_all_news()
    raw_articles = news_fetcher.merge_news_sources(responses)
    print(f"   {len(raw_articles)} articles fetched")

    if max_articles is not None:
        raw_articles = raw_articles[:max_articles]
        print(f"   limited to {len(raw_articles)} for this run")

    print("→ Processing each article (scrape → clean → extract → FinBERT)...")
    processed: list[dict[str, Any]] = []
    for raw in tqdm(raw_articles, desc="articles"):
        record = _process_article(raw)
        if record:
            processed.append(record)
    print(f"   {len(processed)} articles successfully processed")

    if effective_persist and processed:
        print("→ Persisting to Pinecone and MongoDB...")
        try:
            n_pine = vectorstore.upsert_articles(processed)
            print(f"   Pinecone: {n_pine} vectors upserted")
        except Exception as exc:
            print(f"   Pinecone upsert failed: {exc}")
        try:
            n_mongo = mongo_store.insert_articles(processed)
            print(f"   MongoDB: {n_mongo} documents inserted")
        except Exception as exc:
            print(f"   MongoDB insert failed: {exc}")
    else:
        print("→ Skipping persistence (DRY_RUN)")

    print("→ Formatting Bullish / Neutral / Bearish blocks...")
    bullish_text = formatters.format_bullish_block(processed)
    neutral_text = formatters.format_neutral_block(processed)
    bearish_text = formatters.format_bearish_block(processed)
    bullish_count = sum(1 for a in processed if a.get("sentiment") == "Bullish")
    neutral_count = sum(1 for a in processed if a.get("sentiment") == "Neutral")
    bearish_count = sum(1 for a in processed if a.get("sentiment") == "Bearish")

    print(f"   Bullish: {bullish_count} | Neutral: {neutral_count} | Bearish: {bearish_count}")

    print("→ Running 3 sentiment sub-agents (DeepSeek)...")
    bullish_brief = agents.run_sentiment_agent("bullish", bullish_text, bullish_count)
    neutral_brief = agents.run_sentiment_agent("neutral", neutral_text, neutral_count)
    bearish_brief = agents.run_sentiment_agent("bearish", bearish_text, bearish_count)

    print("→ Running main structured agent (Grok + Pinecone RAG)...")
    try:
        retriever_tool = vectorstore.as_retriever_tool()
    except Exception as exc:
        print(f"   Could not init Pinecone retriever tool: {exc}")
        retriever_tool = None

    if retriever_tool is not None:
        executor = agents.build_main_agent(retriever_tool)
        final_report = agents.run_main_agent(
            executor,
            bullish_brief, neutral_brief, bearish_brief,
            bullish_count, neutral_count, bearish_count,
        )
    else:
        final_report = "\n\n".join([
            "📊 OVERVIEW (Pinecone unavailable, no historical context)",
            bullish_brief, neutral_brief, bearish_brief,
        ])

    print("→ Generating audio (OpenAI TTS Opus)...")
    audio_bytes: bytes = b""
    try:
        audio_bytes = tts.generate_audio_opus(final_report)
    except Exception as exc:
        print(f"   TTS failed: {exc}")

    if effective_send:
        print("→ Sending to Telegram...")
        try:
            telegram_io.send_text(final_report)
            if audio_bytes:
                telegram_io.send_audio(audio_bytes, filename="daily_report.opus")
        except Exception as exc:
            print(f"   Telegram send failed: {exc}")
    else:
        print("→ Skipping Telegram send (DRY_RUN)")

    return {
        "report": final_report,
        "audio_bytes": audio_bytes,
        "stats": {
            "articles_fetched": len(raw_articles),
            "articles_processed": len(processed),
            "bullish_count": bullish_count,
            "neutral_count": neutral_count,
            "bearish_count": bearish_count,
        },
        "briefs": {
            "bullish": bullish_brief,
            "neutral": neutral_brief,
            "bearish": bearish_brief,
        },
        "formatted_blocks": {
            "bullish": bullish_text,
            "neutral": neutral_text,
            "bearish": bearish_text,
        },
        "processed_articles": processed,
    }
