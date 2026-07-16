"""
Pipeline Orchestrator for Nate AI Assistant.

Coordinates Speech-to-Text, LLM, and TTS subsystems to process audio recordings,
manage conversational memory, play background filler speech, and track end-to-end latencies.
"""

import time
import random
import threading
import queue
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
    ResponseChunkEvent,
    SpeechSynthesizedEvent,
    SpeechPlaybackCompletedEvent,
    ThinkingStartedEvent,
    ThinkingFinishedEvent,
)
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from tts.fillers import FILLER_PHRASES
from tts.sentence_splitter import StreamingSentenceBuffer
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


class TTSQueue:
    """Queue-based TTS worker for streaming sentence-by-sentence synthesis and playback.
    
    Sentences are enqueued as they arrive from the streaming LLM response.
    A background worker thread synthesizes and plays them sequentially.
    """

    def __init__(self, piper: PiperEngine, player: TTSPlayer, session: ConversationSession) -> None:
        self.piper = piper
        self.player = player
        self.session = session
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background TTS worker thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def enqueue(self, sentence: str) -> None:
        """Add a sentence to the synthesis queue."""
        self._queue.put(sentence)

    def finish(self) -> None:
        """Signal that no more sentences will be added and wait for completion."""
        self._queue.put(None)  # Sentinel
        if self._thread:
            self._thread.join(timeout=30.0)

    def interrupt(self) -> None:
        """Interrupt current playback and drain the queue."""
        self._stop_event.set()
        # Drain remaining items
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put(None)  # Unblock worker
        self.player.stop()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _worker(self) -> None:
        """Background worker: synthesize and play sentences from the queue."""
        first_sentence = True
        while not self._stop_event.is_set():
            try:
                sentence = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if sentence is None:
                break  # Sentinel received

            if self._stop_event.is_set():
                break

            try:
                # Synthesize this sentence
                wav_path = self.piper.synthesize(sentence)

                if self._stop_event.is_set():
                    break

                # Transition to SPEAKING on first sentence
                if first_sentence:
                    self.session.set_state(AssistantState.SPEAKING)
                    first_sentence = False

                self.session.emit(
                    SpeechSynthesizedEvent(
                        wav_path=wav_path,
                        text=sentence,
                        latency_ms=0.0,
                    )
                )

                # Play and block until this sentence finishes
                self.player.play(wav_path, blocking=True)

            except Exception as exc:
                logger.error("TTS queue worker error: %s", exc)


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
        self._interrupt_event = threading.Event()

        logger.info("Pipeline Orchestrator initialized.")

    def interrupt(self) -> None:
        """Interrupt the current pipeline execution (e.g. user started speaking)."""
        self._interrupt_event.set()

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

        # ── Step 2: Streaming LLM Generation + Streaming TTS ─────────────
        return self._streaming_generation()

    def _streaming_generation(self) -> AssistantResponse:
        """Run streaming LLM generation with sentence-level TTS.
        
        Returns:
            AssistantResponse with full assembled text.
        """
        self._interrupt_event.clear()
        
        logger.debug("Routing transcript to Gemini Client (streaming)...")
        
        # Fire ThinkingStartedEvent and update session state
        thinking_start_time = time.time()
        self.session.emit(ThinkingStartedEvent(timestamp=thinking_start_time))
        self.session.set_state(AssistantState.THINKING)

        # Start TTS queue worker if TTS available
        tts_queue = None
        if self.piper is not None and self.player is not None:
            tts_queue = TTSQueue(self.piper, self.player, self.session)
            tts_queue.start()

        sentence_buffer = StreamingSentenceBuffer()
        accumulated_text = ""
        response = None

        try:
            # Query LLM with memory history turns using streaming
            history_contents = self.memory.get_history_for_gemini()
            
            first_chunk = True
            for chunk_text in self.llm.generate_response_stream(history_contents):
                if self._interrupt_event.is_set():
                    logger.info("Pipeline interrupted during streaming.")
                    break

                accumulated_text += chunk_text
                
                # Transition to STREAMING state on first chunk
                if first_chunk:
                    self.session.set_state(AssistantState.STREAMING)
                    first_chunk = False

                # Emit chunk event for frontend
                self.session.emit(
                    ResponseChunkEvent(
                        chunk=chunk_text,
                        accumulated=accumulated_text,
                    )
                )

                # Feed to sentence buffer and enqueue complete sentences for TTS
                if tts_queue:
                    sentences = sentence_buffer.feed(chunk_text)
                    for sentence in sentences:
                        tts_queue.enqueue(sentence)

            # Flush remaining buffered text
            if tts_queue and not self._interrupt_event.is_set():
                remaining = sentence_buffer.flush()
                for sentence in remaining:
                    tts_queue.enqueue(sentence)

            # Get final response from the stream
            response = self.llm.last_stream_result
            if response is None:
                response = AssistantResponse(
                    text=accumulated_text.strip(),
                    prompt_tokens=0,
                    response_tokens=0,
                    latency_ms=(time.time() - thinking_start_time) * 1000.0,
                )

            # Record assistant turn in memory
            self.memory.add_assistant_turn(response.text)

        except Exception as exc:
            logger.error("Streaming LLM Generation failed: %s", exc)
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

        # Emit final ResponseGeneratedEvent
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
        logger.info("  Memory Size        : %d turns", self.memory.total_turns)
        logger.info("  Prompt Tokens      : %d", response.prompt_tokens)
        logger.info("  Response Tokens    : %d", response.response_tokens)
        logger.info("==========================================")

        # Wait for TTS queue to finish playing all sentences
        if tts_queue:
            if self._interrupt_event.is_set():
                tts_queue.interrupt()
            else:
                tts_queue.finish()

            self.session.emit(
                SpeechPlaybackCompletedEvent(
                    wav_path="",
                    duration_ms=0.0,
                )
            )

        self.session.set_state(AssistantState.IDLE)
        logger.info("Pipeline processing completed successfully.")
        return response
