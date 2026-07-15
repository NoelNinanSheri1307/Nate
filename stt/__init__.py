"""
Speech-to-text subsystem for Nate AI Assistant.

Provides Faster-Whisper transcription with structured results
and language detection.
"""

from stt.transcript import Transcript
from stt.whisper_engine import WhisperEngine
from stt.language import get_language_name

__all__ = [
    "Transcript",
    "WhisperEngine",
    "get_language_name",
]
