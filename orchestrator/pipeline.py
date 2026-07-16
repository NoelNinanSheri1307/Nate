"""
Pipeline Orchestrator for Nate AI Assistant.

Coordinates Speech-to-Text and LLM subsystems to process audio recordings and
generate responses while managing session states and latency tracking.
"""

from typing import Optional

from audio.recorder import AudioRecording
from audio.latency import LatencyTracker
from stt.whisper_engine import WhisperEngine
from llm.gemini_client import GeminiClient
from llm.response import AssistantResponse
from orchestrator.state import AssistantState
from orchestrator.session import ConversationSession
from orchestrator.events import (
    RecordingStoppedEvent,
    TranscriptionCompletedEvent,
    ResponseGeneratedEvent,
)
from utils.logger import setup_logger

logger = setup_logger("nate.orchestrator.pipeline")


class Pipeline:
    """Coordinates STT and LLM pipelines and manages session state."""

    def __init__(
        self,
        whisper_engine: WhisperEngine,
        gemini_client: GeminiClient,
        session: Optional[ConversationSession] = None,
        latency_tracker: Optional[LatencyTracker] = None,
    ) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            whisper_engine: The Faster-Whisper Speech-to-Text engine.
            gemini_client: The Gemini client.
            session: The active conversation session.
            latency_tracker: Optional tracker for latency profiling.
        """
        self.whisper = whisper_engine
        self.llm = gemini_client
        self.session = session or ConversationSession()
        self.tracker = latency_tracker

        logger.info("Pipeline Orchestrator initialized.")

    def process_audio(self, audio_recording: AudioRecording) -> AssistantResponse:
        """Process an AudioRecording through the Whisper-Gemini pipeline.

        Args:
            audio_recording: The AudioRecording object containing raw samples.

        Returns:
            AssistantResponse from the LLM.
        """
        logger.info("Pipeline processing started for audio recording.")
        self.session.set_state(AssistantState.THINKING)

        self.session.emit(RecordingStoppedEvent(duration=audio_recording.duration))

        # ── Step 1: Speech-to-Text (Faster-Whisper) ──────────────────────
        logger.debug("Routing audio to Whisper Engine...")
        transcript = self.whisper.transcribe_array(
            audio_recording.samples,
            audio_recording.sample_rate
        )

        if not transcript or transcript.is_empty:
            logger.warning("No transcript produced or audio is silent. Returning empty response.")
            self.session.set_state(AssistantState.IDLE)
            return AssistantResponse(
                text="I didn't catch that. Could you repeat?",
                prompt_tokens=0,
                response_tokens=0,
                latency_ms=0.0
            )

        self.session.emit(
            TranscriptionCompletedEvent(
                text=transcript.text,
                language=transcript.language,
                processing_time=transcript.processing_time,
            )
        )
        self.session.add_history("user", transcript.text)

        # ── Step 2: Language Model (Gemini) ──────────────────────────────
        logger.debug("Routing transcript to Gemini Client...")
        try:
            response = self.llm.generate_response(transcript.text)
        except Exception as exc:
            logger.error("LLM Generation failed: %s", exc)
            self.session.set_state(AssistantState.ERROR)
            return AssistantResponse(
                text="I'm sorry, I'm having trouble connecting right now.",
                prompt_tokens=0,
                response_tokens=0,
                latency_ms=0.0
            )

        self.session.emit(
            ResponseGeneratedEvent(
                text=response.text,
                latency_ms=response.latency_ms,
            )
        )
        self.session.add_history("assistant", response.text)

        self.session.set_state(AssistantState.IDLE)
        logger.info("Pipeline processing completed successfully.")
        return response
