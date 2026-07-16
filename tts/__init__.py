"""
Text-to-Speech Subsystem using Piper.
"""

from tts.voices import DEFAULT_VOICE
from tts.models import TTSConfig
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from tts.exceptions import TTSError, TTSInitializationError, TTSSynthesisError

__all__ = [
    "DEFAULT_VOICE",
    "TTSConfig",
    "PiperEngine",
    "TTSPlayer",
    "TTSError",
    "TTSInitializationError",
    "TTSSynthesisError",
]
