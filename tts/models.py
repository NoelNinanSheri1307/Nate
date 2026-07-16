"""
Configuration models for the TTS subsystem.
"""

from dataclasses import dataclass
import config


@dataclass(frozen=True)
class TTSConfig:
    """Configuration options for Piper TTS."""
    voice: str = config.DEFAULT_TTS_VOICE
    model_path: str = config.PIPER_MODEL_PATH
    executable_path: str = config.PIPER_EXECUTABLE_PATH
