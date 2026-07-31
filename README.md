# Financial News Agent

> A no-code n8n workflow rebuilt as production shaped Python, so it could be versioned, tested and actually understood.

An automated pipeline that collects financial and crypto news, classifies sentiment with FinBERT, synthesises it through a team of specialised LLM agents, and delivers a structured daily brief to Telegram as both text and audio. A second flow answers follow up questions conversationally, by text or by voice.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-agents-1C3C3C?logo=langchain&logoColor=white)
![FinBERT](https://img.shields.io/badge/FinBERT-sentiment-FFD21E?logo=huggingface&logoColor=black)
![Pinecone](https://img.shields.io/badge/Pinecone-RAG-000000)
![MongoDB](https://img.shields.io/badge/MongoDB-memory-47A248?logo=mongodb&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-delivery-26A5E4?logo=telegram&logoColor=white)

---

## Why this project

The original system was an n8n workflow with two flows, and it worked. The problem with a working no-code workflow is everything around it: you cannot diff it, you cannot unit test a node, you cannot review it, and the logic lives inside a UI rather than in code anyone can read.

This repository is that workflow rebuilt in Python, with both flows reproduced faithfully as runnable notebooks on top of a `src/` package of reusable modules. The interesting part was not translating node to function. It was deciding where the n8n abstractions were load bearing and where they were hiding complexity that deserved to be explicit, such as the parallel fetching, the retry behaviour and the persistence layer.

## Architecture

### Daily pipeline (`notebooks/01_daily_pipeline.ipynb`)

```
NewsData.io (5 sources, fetched in parallel)
    -> merge and split
    -> scrape each article link
    -> HTML cleaning
    -> information extraction (DeepSeek)
    -> FinBERT sentiment classification (HuggingFace Inference API)
    -> metadata aggregation
    -> [Pinecone upsert + MongoDB insert]
    -> format into Bullish / Neutral / Bearish blocks
    -> 3 specialised sub-agents (DeepSeek)
    -> main agent (Grok) with a Pinecone RAG tool
    -> Telegram delivery (text + Opus TTS audio)
```

### Conversational agent (`notebooks/02_conversational_agent.ipynb`)

```
Telegram message (text or voice)
    -> if voice: download and transcribe with Whisper
    -> conversational agent (Grok + MongoDB memory + Pinecone tool)
    -> reply in the original modality (text or TTS audio)
```

The agent hierarchy is the design choice worth pointing at. Three sub-agents each summarise one sentiment bucket, and a main agent composes their outputs into a single brief while retaining a retrieval tool over the Pinecone history. That keeps each prompt narrow and gives the main agent access to context beyond the current day's articles.

## Stack

| Layer | Technology |
|-------|-----------|
| News source | NewsData.io, 5 endpoints fetched concurrently with `ThreadPoolExecutor` |
| Sentiment | FinBERT (`ProsusAI/finbert`) via the HuggingFace Inference API |
| LLMs | DeepSeek (extraction and sub-agents) and Grok (main and conversational agent), routed through OpenRouter |
| Orchestration | LangChain agents |
| Vector store | Pinecone, used as the RAG retrieval tool |
| Persistence | MongoDB, for article history and chat memory |
| Speech | OpenAI Whisper for transcription, Opus TTS for audio replies |
| Delivery | Telegram Bot API |

## Repository structure

```
src/
  config.py            Settings loaded from .env
  news_fetcher.py      The 5 NewsData.io endpoints plus merge logic
  scraper.py           HTML fetch, cleaning, LLM extraction
  finbert.py           HuggingFace Inference API client
  aggregator.py        Builds the per article record
  formatters.py        Bullish / Neutral / Bearish text blocks
  llm.py               Chat model factory over OpenRouter
  agents.py            Sub-agents, main agent, conversational agent
  vectorstore.py       Pinecone upsert plus retriever tool
  mongo_store.py       Article history and chat memory
  tts.py               OpenAI Opus TTS
  telegram_io.py       Send text and audio, download voice, polling
  pipeline.py          The run_daily_pipeline orchestrator
notebooks/
  01_daily_pipeline.ipynb
  02_conversational_agent.ipynb
```

## Setup

```bash
git clone https://github.com/BogdanT54/financial-news-agent.git
cd financial-news-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your API keys
jupyter notebook
```

On Google Colab:

```python
!git clone https://github.com/BogdanT54/financial-news-agent.git
%cd financial-news-agent
!pip install -r requirements.txt

# Upload your .env from the Files panel, then:
from src.config import get_settings
settings = get_settings()
print("Loaded:", settings.PINECONE_INDEX, "DRY_RUN:", settings.DRY_RUN)
```

Colab Secrets are supported as an alternative to uploading a `.env` file.

## DRY_RUN mode

`DRY_RUN=true` is the default in `.env`. In this mode the pipeline:

- runs the full fetch, scrape, FinBERT classification and LLM agent chain
- displays the final report and the audio inline in the notebook
- does **not** send anything to Telegram
- does **not** write to Pinecone or MongoDB

This makes the project safe to demo without side effects. For a live run set `DRY_RUN=false` in `.env`, or override the arguments directly in the notebook, and rerun the pipeline cell.

## Model configuration

The LLM model ids are configurable from `.env`, so swapping providers needs no code change:

```
MODEL_SUB_AGENT=deepseek/deepseek-v4-flash
MODEL_MAIN_AGENT=x-ai/grok-4.3
MODEL_EXTRACTOR=deepseek/deepseek-v4-flash
```

If OpenRouter rejects a model id, replace it with the nearest available variant (for example `deepseek/deepseek-chat-v3.1` or `x-ai/grok-4`) without touching the code.

## Team

Built for the Natural Language Processing course by Bogdan Tofan, Alina-Alexandra Manea and Alina Burcă.
