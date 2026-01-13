# cogs/transcription/service.py
from __future__ import annotations
import io
from typing import Protocol, Optional

class SpeechToText(Protocol):
    async def transcribe(self, audio_bytes: io.BytesIO, filename: str, user_id: int) -> Optional[str]:
        ...

class NullSTT:
    """
    Default no-op STT service. Replace with your provider (Whisper, Deepgram, etc.)
    """
    async def transcribe(self, audio_bytes: io.BytesIO, filename: str, user_id: int) -> Optional[str]:
        # Return None/"" to skip replying; swap in a real implementation.
        return ""

# Example: You can later wire a real provider:
# class WhisperSTT:
#     def __init__(self, model: str = "large-v3"):
#         self.model = model
#     async def transcribe(self, audio_bytes: io.BytesIO, filename: str, user_id: int) -> Optional[str]:
#         # call your Whisper code here
#         return "transcribed text"
