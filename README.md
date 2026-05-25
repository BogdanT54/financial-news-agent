# Financial News Agent

Port în Python al workflow-ului N8N care preia știri financiare / crypto,
le clasifică sentimentul cu FinBERT, le sintetizează prin agenți LLM
specializați și livrează un brief structurat pe Telegram, text + audio.

Implementarea originală era un workflow N8N cu două flow-uri (`Daily
news agent` + `Conversational agent`). Acest repository reproduce ambele
flow-uri ca proiect Python rulabil, organizat în două notebook-uri
Jupyter plus un pachet `src/` cu module reutilizabile.

## Arhitectură

### Pipeline-ul zilnic (`notebooks/01_daily_pipeline.ipynb`)

```
NewsData.io (5 surse, în paralel)
    -> merge + split
    -> scraping pe linkul fiecărui articol
    -> curățare HTML
    -> Information Extractor (DeepSeek)
    -> clasificare FinBERT (HuggingFace)
    -> agregare metadate
    -> [Pinecone upsert + Mongo insert]
    -> formatare blocuri Bullish / Neutral / Bearish
    -> 3 sub-agenți specializați (DeepSeek)
    -> Agent principal (Grok) cu tool de RAG pe Pinecone
    -> Telegram (text + audio Opus TTS)
```

### Agentul conversațional (`notebooks/02_conversational_agent.ipynb`)

```
Mesaj Telegram (text sau voce)
    -> dacă e voce: download + transcribere Whisper
    -> Agent conversațional (Grok + memorie Mongo + tool Pinecone)
    -> răspuns în modalitatea originală (text sau audio TTS)
```

## Setup

### Local

```bash
git clone https://github.com/BogdanT54/financial-news-agent.git
cd financial-news-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editează .env și completează cheile API
jupyter notebook
```

### Google Colab

```python
!git clone https://github.com/BogdanT54/financial-news-agent.git
%cd financial-news-agent
!pip install -r requirements.txt

# Încarcă fișierul .env din panel-ul Files, apoi:
from src.config import get_settings
settings = get_settings()
print("Încărcat:", settings.PINECONE_INDEX, "DRY_RUN:", settings.DRY_RUN)
```

## Mod DRY_RUN

Implicit `DRY_RUN=true` în `.env`. În acest mod pipeline-ul:

- rulează tot fetching-ul, scraping-ul, clasificarea FinBERT și agenții LLM
- afișează raportul final și audio-ul inline în notebook
- **nu** trimite nimic pe Telegram
- **nu** scrie în Pinecone sau MongoDB

Pentru o rulare live setează `DRY_RUN=false` în `.env` (sau suprascrie
în notebook) și re-rulează celula pipeline-ului.

## Configurare modele

Id-urile modelelor LLM sunt configurabile din `.env`:

```
MODEL_SUB_AGENT=deepseek/deepseek-v4-flash
MODEL_MAIN_AGENT=x-ai/grok-4.3
MODEL_EXTRACTOR=deepseek/deepseek-v4-flash
```

Dacă OpenRouter respinge un id de model, înlocuiește-l cu cea mai
apropiată variantă disponibilă (de exemplu `deepseek/deepseek-chat-v3.1`
sau `x-ai/grok-4`) fără să modifici codul.

## Structura proiectului

```
src/
  config.py            setări încărcate din .env
  news_fetcher.py      cele 5 endpoint-uri NewsData.io + merge
  scraper.py           fetch HTML, curățare, extracție LLM
  finbert.py           client HuggingFace Inference API
  aggregator.py        construiește înregistrarea per articol
  formatters.py        blocuri text Bullish / Neutral / Bearish
  llm.py               factory pentru chat model pe OpenRouter
  agents.py            sub-agenți, agent principal, conversațional
  vectorstore.py       upsert Pinecone + retriever tool
  mongo_store.py       istoric articole + memorie chat
  tts.py               OpenAI Opus TTS
  telegram_io.py       trimitere text/audio, download voce, polling
  pipeline.py          orchestratorul run_daily_pipeline
notebooks/
  01_daily_pipeline.ipynb
  02_conversational_agent.ipynb
```

## Echipa

Tofan Bogdan, Manea Alina-Alexandra, Burcă Alina.
Materia: NLP.
