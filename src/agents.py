"""Sub-agenți (Bullish/Neutral/Bearish), agent principal, agent conversațional."""
from datetime import datetime
from typing import Any, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from . import prompts
from .config import get_settings
from .llm import get_openrouter_llm


def _now() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


def _now_long() -> str:
    return datetime.now().strftime("%d %B %Y, %H:%M")


# ─────────────────────────────────────────────────────────────────────
# Sub-agenți: Bullish / Neutral / Bearish
# ─────────────────────────────────────────────────────────────────────

_SUB_TEMPLATES = {
    "bullish": (prompts.BULLISH_SYSTEM, prompts.BULLISH_USER),
    "neutral": (prompts.NEUTRAL_SYSTEM, prompts.NEUTRAL_USER),
    "bearish": (prompts.BEARISH_SYSTEM, prompts.BEARISH_USER),
}


def run_sentiment_agent(
    sentiment: str,
    formatted_text: str,
    article_count: int,
    model: Optional[str] = None,
) -> str:
    """Rulează unul din cei 3 sub-agenți (DeepSeek) cu prompt-ul corespunzător."""
    sentiment_key = sentiment.lower()
    if sentiment_key not in _SUB_TEMPLATES:
        raise ValueError(f"Sentiment necunoscut: {sentiment}")
    system_tpl, user_tpl = _SUB_TEMPLATES[sentiment_key]

    settings = get_settings()
    llm = get_openrouter_llm(model or settings.MODEL_SUB_AGENT, temperature=0.3)

    date_str = _now_long()
    system_msg = SystemMessage(content=system_tpl.format(
        date=date_str,
        article_count=article_count,
    ))
    user_msg = HumanMessage(content=user_tpl.format(
        text=formatted_text,
        article_count=article_count,
        date=_now(),
    ))

    result = llm.invoke([system_msg, user_msg])
    return result.content if hasattr(result, "content") else str(result)


# ─────────────────────────────────────────────────────────────────────
# Main structured agent (cu RAG Pinecone)
# ─────────────────────────────────────────────────────────────────────

def build_main_agent(
    retriever_tool: BaseTool,
    model: Optional[str] = None,
    memory_messages: Optional[list] = None,
) -> AgentExecutor:
    """Construiește agentul principal (Grok) cu acces la Pinecone tool."""
    settings = get_settings()
    llm = get_openrouter_llm(model or settings.MODEL_MAIN_AGENT, temperature=0.2)

    system_text = prompts.MAIN_SYSTEM.format(date=_now_long())

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, [retriever_tool], prompt)
    return AgentExecutor(agent=agent, tools=[retriever_tool], verbose=False)


def run_main_agent(
    executor: AgentExecutor,
    bullish_brief: str,
    neutral_brief: str,
    bearish_brief: str,
    bullish_count: int,
    neutral_count: int,
    bearish_count: int,
) -> str:
    combined = (
        f"=== BULLISH BRIEF ({bullish_count} articles) ===\n{bullish_brief}\n\n"
        f"=== NEUTRAL BRIEF ({neutral_count} articles) ===\n{neutral_brief}\n\n"
        f"=== BEARISH BRIEF ({bearish_count} articles) ===\n{bearish_brief}\n"
    )

    user_text = prompts.MAIN_USER.format(
        combined_briefs=combined,
        bullish_count=bullish_count,
        date=_now(),
    )

    result = executor.invoke({"input": user_text})
    return result.get("output", "") if isinstance(result, dict) else str(result)


# ─────────────────────────────────────────────────────────────────────
# Conversational agent
# ─────────────────────────────────────────────────────────────────────

def build_conversational_agent(
    retriever_tool: BaseTool,
    model: Optional[str] = None,
) -> AgentExecutor:
    """Construiește agentul conversațional pentru Telegram (Grok + Pinecone RAG)."""
    settings = get_settings()
    llm = get_openrouter_llm(model or settings.MODEL_MAIN_AGENT, temperature=0.1)

    system_text = prompts.CONVERSATIONAL_SYSTEM.format(date=_now_long())

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, [retriever_tool], prompt)
    return AgentExecutor(agent=agent, tools=[retriever_tool], verbose=False)


def run_conversational_agent(
    executor: AgentExecutor,
    user_message: str,
    chat_history: Optional[list] = None,
) -> str:
    payload: dict[str, Any] = {"input": user_message}
    if chat_history is not None:
        payload["chat_history"] = chat_history
    result = executor.invoke(payload)
    return result.get("output", "") if isinstance(result, dict) else str(result)
