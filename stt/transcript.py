"""
Transcript dataclass for structured STT results.

Provides a clean, typed representation of a transcription result
with all relevant metadata.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Transcript:
    """Structured result of a speech-to-text transcription.

    Attributes:
        text: The transcribed text.
        language: Detected or specified language code (e.g. "en").
        confidence: Estimated confidence score (0.0 to 1.0).
        duration: Duration of the source audio in seconds.
        processing_time: Time taken to transcribe in seconds.
    """

    text: str
    language: str
    confidence: float
    duration: float
    processing_time: float

    @property
    def is_empty(self) -> bool:
        """Whether the transcription produced no text."""
        return not self.text or not self.text.strip()

    def __str__(self) -> str:
        return (
            f"Transcript(lang={self.language}, confidence={self.confidence:.2f}, "
            f"duration={self.duration:.2f}s, processing={self.processing_time:.3f}s)\n"
            f"  \"{self.text}\""
        )
