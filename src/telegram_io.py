"""I/O Telegram: trimitere text/audio, download voce, polling bot."""
import asyncio
import io
from typing import Awaitable, Callable, Optional

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import get_settings


def _bot_token() -> str:
    return get_settings().TELEGRAM_BOT_TOKEN


def _default_chat_id() -> str:
    return get_settings().TELEGRAM_CHAT_ID


# ─────────────────────────────────────────────────────────────────────
# Trimitere sincronă (apelată din pipeline-ul zilnic)
# ─────────────────────────────────────────────────────────────────────

async def _send_text_async(chat_id: str, text: str) -> None:
    from telegram import Bot
    bot = Bot(token=_bot_token())
    await bot.send_message(chat_id=chat_id, text=text)


async def _send_audio_async(chat_id: str, audio_bytes: bytes, filename: str) -> None:
    from telegram import Bot
    bot = Bot(token=_bot_token())
    await bot.send_audio(chat_id=chat_id, audio=io.BytesIO(audio_bytes), filename=filename)


def send_text(text: str, chat_id: Optional[str] = None) -> None:
    chat = chat_id or _default_chat_id()
    asyncio.run(_send_text_async(chat, text))


def send_audio(audio_bytes: bytes, filename: str = "report.opus", chat_id: Optional[str] = None) -> None:
    chat = chat_id or _default_chat_id()
    asyncio.run(_send_audio_async(chat, audio_bytes, filename))


# ─────────────────────────────────────────────────────────────────────
# Download voce (folosit de agentul conversațional)
# ─────────────────────────────────────────────────────────────────────

async def download_voice(file_id: str) -> bytes:
    from telegram import Bot
    bot = Bot(token=_bot_token())
    tg_file = await bot.get_file(file_id)
    buf = io.BytesIO()
    await tg_file.download_to_memory(out=buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────
# Bot polling (agent conversațional)
# ─────────────────────────────────────────────────────────────────────

MessageHandlerFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def run_bot_polling(handler: MessageHandlerFn) -> None:
    """Pornește bot-ul în polling mode cu handler-ul dat.

    Handler-ul primește (update, context) și trebuie să răspundă manual prin
    `context.bot.send_message(...)` sau similar.
    """
    app = Application.builder().token(_bot_token()).build()
    app.add_handler(MessageHandler(filters.ALL, handler))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
