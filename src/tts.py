"""Text-to-speech prin OpenAI (format Opus, ca în N8N)."""
from openai import OpenAI

from .config import get_settings


def generate_audio_opus(text: str, voice: str = "alloy", model: str = "tts-1") -> bytes:
    """Generează audio Opus din text. Întoarce bytes."""
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="opus",
    )
    return response.read()


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Whisper: voce → text."""
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes),
    )
    return response.text
