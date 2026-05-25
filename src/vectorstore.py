"""Pinecone vector store: upsert articole + retriever tool pentru agenți."""
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from .config import get_settings


def _embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)


def init_pinecone(index_name: Optional[str] = None) -> PineconeVectorStore:
    settings = get_settings()
    name = index_name or settings.PINECONE_INDEX
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return PineconeVectorStore(
        index=pc.Index(name),
        embedding=_embeddings(),
    )


def _article_to_document(article: dict[str, Any]) -> Document:
    """Construiește documentul + metadata identic cu Default Data Loader din N8N."""
    country_list = article.get("country") or []
    country = country_list[0] if country_list else ""

    text = "\n\n".join([
        article.get("title", ""),
        article.get("description", ""),
        article.get("article_content", ""),
    ]).strip()

    metadata = {
        "article_id": article.get("article_id", ""),
        "link": article.get("link", ""),
        "title": article.get("title", ""),
        "description": article.get("description", ""),
        "source": "news_api",
        "country": country,
        "finbert_score": float(article.get("finbert_score", 0.0)),
        "finbert_label": article.get("finbert_label", ""),
        "publishing_date": article.get("pubDate", ""),
        "article_content": article.get("article_content", ""),
    }
    return Document(page_content=text, metadata=metadata)


def upsert_articles(articles: list[dict[str, Any]], store: Optional[PineconeVectorStore] = None) -> int:
    """Inserează articolele în Pinecone (un vector / articol). Întoarce numărul scris."""
    if not articles:
        return 0
    vector_store = store or init_pinecone()
    documents = [_article_to_document(a) for a in articles]
    ids = [a.get("article_id") or a.get("link") or str(i) for i, a in enumerate(articles)]
    vector_store.add_documents(documents=documents, ids=ids)
    return len(documents)


def get_index_stats(index_name: Optional[str] = None) -> dict[str, Any]:
    """Returnează statisticile indexului Pinecone (total vectori, dimensiune etc.)."""
    settings = get_settings()
    name = index_name or settings.PINECONE_INDEX
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    stats = pc.Index(name).describe_index_stats()
    return {
        "total_vector_count": stats.get("total_vector_count", stats.total_vector_count if hasattr(stats, "total_vector_count") else "N/A"),
        "dimension": stats.get("dimension", stats.dimension if hasattr(stats, "dimension") else "N/A"),
        "namespaces": dict(stats.get("namespaces", {})),
    }


def as_retriever_tool(
    name: str = "fin_news_vector_search",
    description: str = "Retrieve similar news relating to the provided query from the financial news vector store.",
    top_k: int = 40,
    store: Optional[PineconeVectorStore] = None,
) -> Tool:
    """Expune Pinecone-ul ca tool LangChain pentru agenți."""
    vector_store = store or init_pinecone()
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})

    def _run(query: str) -> str:
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant historical articles found."
        out_lines = []
        for i, doc in enumerate(docs, 1):
            m = doc.metadata
            out_lines.append(
                f"[{i}] {m.get('title', '')} — {m.get('publishing_date', '')[:10]} "
                f"({m.get('finbert_label', '')}, score {m.get('finbert_score', 0):.2f})\n"
                f"    {m.get('description', '')[:300]}\n"
                f"    link: {m.get('link', '')}"
            )
        return "\n".join(out_lines)

    return Tool(name=name, description=description, func=_run)
