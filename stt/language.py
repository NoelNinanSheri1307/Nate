"""
Language detection and mapping utilities for STT.

Provides language code to display name mapping and
helpers for the Whisper engine.
"""

# Subset of languages commonly supported by Whisper
LANGUAGE_MAP: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "nl": "Dutch",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "uk": "Ukrainian",
}


def get_language_name(code: str) -> str:
    """Get the display name for a language code.

    Args:
        code: ISO 639-1 language code (e.g. "en").

    Returns:
        Human-readable language name, or the code itself if unknown.
    """
    return LANGUAGE_MAP.get(code, code)
