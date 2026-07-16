"""
Pipeline Orchestrator for Nate AI Assistant.

Coordinates Speech-to-Text, LLM, and TTS subsystems to process audio recordings,
manage conversational memory, play background filler speech, and track end-to-end latencies.
"""

import time
import random
import threading
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
    ThinkingStartedEvent,
    ThinkingFinishedEvent,
)
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from tts.fillers import FILLER_PHRASES
from memory.manager import MemoryManager
from utils.logger import setup_logger

logger = setup_logger("nate.orchestrator.pipeline")


class BackgroundFiller:
    """Manages playing a random filler phrase in the background if latency exceeds 800ms."""

    def __init__(self, piper: PiperEngine, player: TTSPlayer) -> None:
        self.piper = piper
        self.player = player
        self.stop_event = threading.Event()
        self.filler_phrase: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        self.triggered = False

    def start(self) -> None:
        """Start the background checking thread."""
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop the check and interrupt playback if the filler phrase started playing."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=0.2)
        if self.triggered:
            logger.info("[FILLER] Interrupted filler playback due to Gemini completion.")
            self.player.stop()

    def _run(self) -> None:
        # Wait for 800ms
        exceeded = not self.stop_event.wait(0.8)
        if exceeded and not self.stop_event.is_set():
            self.filler_phrase = random.choice(FILLER_PHRASES)
            logger.info("[FILLER] Latency exceeded 800ms limit. Selected filler: '%s'", self.filler_phrase)
            try:
                self.triggered = True
                wav_path = self.piper.synthesize(self.filler_phrase)
                if not self.stop_event.is_set():
                    # Play non-blocking to allow interruption when Gemini completes
                    self.player.play(wav_path, blocking=False)
            except Exception as exc:
                logger.error("[FILLER] Speech synthesis of filler phrase failed: %s", exc)
                self.triggered = False



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
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            whisper_engine: The Faster-Whisper Speech-to-Text engine.
            gemini_client: The Gemini client.
            session: The active conversation session.
            latency_tracker: Optional tracker for latency profiling.
            piper_engine: Optional Piper TTS engine.
            tts_player: Optional TTS playback player.
            memory_manager: Optional MemoryManager interface.
        """
        self.whisper = whisper_engine
        self.llm = gemini_client
        self.session = session or ConversationSession()
        self.tracker = latency_tracker
        self.piper = piper_engine
        self.player = tts_player
        self.memory = memory_manager or MemoryManager(default_limit=8)

        logger.info("Pipeline Orchestrator initialized.")

    def process_audio(self, audio_recording: AudioRecording) -> AssistantResponse:
        """Process an AudioRecording through the Whisper-Gemini-Piper pipeline.

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
        
        # Store user turn in memory
        self.memory.add_user_turn(transcript.text)

        # ── Step 2: Language Model (Gemini) ──────────────────────────────
        logger.debug("Routing transcript to Gemini Client...")
        
        # Fire ThinkingStartedEvent and update session state
        thinking_start_time = time.time()
        self.session.emit(ThinkingStartedEvent(timestamp=thinking_start_time))
        self.session.set_state(AssistantState.THINKING)

        # Start Background Filler Trigger
        filler = None
        if self.piper is not None and self.player is not None:
            filler = BackgroundFiller(self.piper, self.player)
            filler.start()

        response = None
        try:
            # Query LLM with memory history turns instead of raw text
            history_contents = self.memory.get_history_for_gemini()
            response = self.llm.generate_response(history_contents)
            
            # Record assistant turn in memory upon successful generation
            self.memory.add_assistant_turn(response.text)

        except Exception as exc:
            logger.error("LLM Generation failed: %s", exc)
            self.session.set_state(AssistantState.ERROR)
            response = AssistantResponse(
                text="I'm sorry, I'm having trouble connecting right now.",
                prompt_tokens=0,
                response_tokens=0,
                latency_ms=0.0
            )
        finally:
            # Measure thinking duration
            thinking_duration_ms = (time.time() - thinking_start_time) * 1000.0
            
            # Fire ThinkingFinishedEvent
            self.session.emit(
                ThinkingFinishedEvent(
                    timestamp=time.time(),
                    duration_ms=thinking_duration_ms,
                )
            )

            # Stop background filler if running
            if filler is not None:
                filler.stop()

        self.session.emit(
            ResponseGeneratedEvent(
                text=response.text,
                latency_ms=response.latency_ms,
            )
        )
        self.session.add_history("assistant", response.text)

        # Detailed Logging
        logger.info("==========================================")
        logger.info("  DIAGNOSTICS & CONVERSATIONAL METRICS")
        logger.info("==========================================")
        logger.info("  Conversation Turn  : %d", self.memory.total_turns)
        logger.info("  Thinking Duration  : %.2f ms", thinking_duration_ms)
        logger.info("  Filler Phrase Used : %s", filler.filler_phrase if (filler and filler.triggered) else "None")
        logger.info("  Memory Size        : %d turns", self.memory.total_turns)
        logger.info("  Prompt Tokens      : %d", response.prompt_tokens)
        logger.info("  Response Tokens    : %d", response.response_tokens)
        logger.info("  Conversation Length: %d turns", self.memory.total_turns)
        logger.info("==========================================")

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
