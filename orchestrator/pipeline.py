"""
Pipeline Orchestrator for Nate AI Assistant.

Coordinates Speech-to-Text and LLM subsystems to process audio recordings and
generate responses while managing session states and latency tracking.
"""

import time
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
    SpeechSynthesizedEvent,
    SpeechPlaybackCompletedEvent,
)
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
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
        piper_engine: Optional[PiperEngine] = None,
        tts_player: Optional[TTSPlayer] = None,
    ) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            whisper_engine: The Faster-Whisper Speech-to-Text engine.
            gemini_client: The Gemini client.
            session: The active conversation session.
            latency_tracker: Optional tracker for latency profiling.
            piper_engine: Optional Piper TTS engine.
            tts_player: Optional TTS playback player.
        """
        self.whisper = whisper_engine
        self.llm = gemini_client
        self.session = session or ConversationSession()
        self.tracker = latency_tracker
        self.piper = piper_engine
        self.player = tts_player

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

        # ── Step 3: Text-to-Speech (Piper) & Playback ─────────────────────
        if self.piper is not None:
            try:
                self.session.set_state(AssistantState.SPEAKING)
                
                # Synthesize Speech
                synthesis_start = time.perf_counter()
                wav_path = self.piper.synthesize(response.text)
                synthesis_latency_ms = (time.perf_counter() - synthesis_start) * 1000.0
                
                self.session.emit(
                    SpeechSynthesizedEvent(
                        wav_path=wav_path,
                        text=response.text,
                        latency_ms=synthesis_latency_ms,
                    )
                )

                # Play Speech
                if self.player is not None:
                    playback_start = time.perf_counter()
                    
                    # Measure start-of-playback latency using tracker if configured
                    if self.tracker:
                        self.tracker.start_timer("playback")

                    # Perform blocking playback
                    self.player.play(wav_path, blocking=True)
                    
                    playback_latency_ms = (time.perf_counter() - playback_start) * 1000.0

                    self.session.emit(
                        SpeechPlaybackCompletedEvent(
                            wav_path=wav_path,
                            duration_ms=playback_latency_ms,
                        )
                    )

            except Exception as exc:
                logger.error("TTS synthesis or playback failed: %s. Falling back to console output.", exc)
                # Keep session in IDLE state on failure
                self.session.set_state(AssistantState.IDLE)

        self.session.set_state(AssistantState.IDLE)
        logger.info("Pipeline processing completed successfully.")
        return response
