"""
Configuration module for Nate AI Assistant.

Loads environment variables, validates required settings,
and exposes configuration constants for all modules.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


# ─── API Keys ────────────────────────────────────────────────────────────────

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


# ─── Audio Settings (placeholders for future phases) ─────────────────────────

SAMPLE_RATE: int = 16_000          # Hz, standard for speech recognition
CHANNELS: int = 1                  # Mono audio
BLOCK_SIZE: int = 512              # Frames per buffer
AUDIO_FORMAT: str = "int16"        # Audio sample format


# ─── VAD Settings (placeholders) ─────────────────────────────────────────────

VAD_THRESHOLD: float = 0.5         # Silero VAD speech probability threshold
SILENCE_DURATION: float = 1.0      # Seconds of silence before end-of-speech


# ─── STT Settings ────────────────────────────────────────────────────────────

STT_MODEL_SIZE: str = os.getenv("WHISPER_MODEL", os.getenv("STT_MODEL_SIZE", "small"))  # tiny, base, small, medium, large-v3
STT_BEAM_SIZE: int = int(os.getenv("STT_BEAM_SIZE", "5"))



# ─── LLM Settings (placeholders) ─────────────────────────────────────────────

LLM_MODEL: str = os.getenv("GEMINI_MODEL", os.getenv("LLM_MODEL", "gemini-3.5-flash"))
LLM_MAX_TOKENS: int = 256
LLM_TEMPERATURE: float = 0.7
ENABLE_LLM_CACHE: bool = os.getenv("ENABLE_LLM_CACHE", "False").lower() in ("true", "1", "yes")


# ─── TTS Settings (placeholders) ─────────────────────────────────────────────

TTS_MODEL_PATH: str = os.path.join("models", "piper")
TTS_SPEAKER: str = "default"


# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR: str = "logs"


# ─── Paths ───────────────────────────────────────────────────────────────────

PROJECT_ROOT: str = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR: str = os.path.join(PROJECT_ROOT, "assets")
MODELS_DIR: str = os.path.join(PROJECT_ROOT, "models")


# ─── Validation ──────────────────────────────────────────────────────────────

def validate_config() -> bool:
    """Validate that all required configuration values are present.

    Returns:
        True if configuration is valid, False otherwise.
    """
    errors: list[str] = []

    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set. Add it to your .env file.")

    if errors:
        for error in errors:
            print(f"  [CONFIG ERROR] {error}", file=sys.stderr)
        return False

    return True
