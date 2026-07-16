"""
Event definitions for the Orchestrator pipeline.
"""

from dataclasses import dataclass
from typing import Any
from orchestrator.state import AssistantState


@dataclass(frozen=True)
class PipelineEvent:
    """Base class for all pipeline events."""
    pass


@dataclass(frozen=True)
class StateChangedEvent(PipelineEvent):
    """Fired when the assistant changes its state."""
    old_state: AssistantState
    new_state: AssistantState


@dataclass(frozen=True)
class RecordingStartedEvent(PipelineEvent):
    """Fired when recording starts."""
    file_path: str


@dataclass(frozen=True)
class RecordingStoppedEvent(PipelineEvent):
    """Fired when recording stops."""
    duration: float


@dataclass(frozen=True)
class TranscriptionCompletedEvent(PipelineEvent):
    """Fired when Whisper transcription is done."""
    text: str
    language: str
    processing_time: float


@dataclass(frozen=True)
class ResponseGeneratedEvent(PipelineEvent):
    """Fired when Gemini generation is complete."""
    text: str
    latency_ms: float


@dataclass(frozen=True)
class SpeechSynthesizedEvent(PipelineEvent):
    """Fired when Piper speech synthesis is complete."""
    wav_path: str
    text: str
    latency_ms: float


@dataclass(frozen=True)
class SpeechPlaybackCompletedEvent(PipelineEvent):
    """Fired when speech playback has finished."""
    wav_path: str
    duration_ms: float


@dataclass(frozen=True)
class ThinkingStartedEvent(PipelineEvent):
    """Fired when Gemini generation begins."""
    timestamp: float


@dataclass(frozen=True)
class ThinkingFinishedEvent(PipelineEvent):
    """Fired when Gemini generation finishes."""
    timestamp: float
    duration_ms: float
