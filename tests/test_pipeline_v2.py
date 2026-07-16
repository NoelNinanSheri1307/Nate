"""
Phase 6 — Conversational Intelligence Layer Integration Test.

Performs a full pass:
1. Records audio from microphone with VAD auto-stop.
2. Processes through the v2 Pipeline with:
   - Conversation Memory (tracking turns).
   - Background Filler Speech triggering if Gemini takes >800ms.
   - Event raising (ThinkingStarted, ThinkingFinished, etc.).
3. Speaks response and prints latency metrics.
"""

import sys
import os
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from audio.recorder import AudioRecorder, RecordingConfig
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker
from stt.whisper_engine import WhisperEngine
from llm.gemini_client import GeminiClient
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from memory.manager import MemoryManager
from orchestrator.session import ConversationSession
from orchestrator.pipeline import Pipeline
from orchestrator.events import PipelineEvent
from utils.logger import setup_logger

logger = setup_logger("nate.test.pipeline_v2", level="DEBUG")


def main() -> None:
    """Run the complete Phase 6 integration test."""
    print("\n" + "=" * 60)
    print("  NATE — Phase 6 Conversational Intelligence Test")
    print("=" * 60)

    if not config.validate_config():
        print("  [ERROR] Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
        sys.exit(1)

    tracker = LatencyTracker()
    session = ConversationSession()
    memory = MemoryManager(default_limit=8)

    # Register event logger
    def event_logger(event: PipelineEvent) -> None:
        logger.info("[EVENT] Raised: %s", event.__class__.__name__)

    session.register_listener(event_logger)

    # ── Step 1: Initialize Subsystems ────────────────────────────────────
    print("\n--- Step 1: Initializing Subsystems ---\n")
    vad = VoiceActivityDetector(threshold=0.5, silence_duration=1.5)
    
    rec_config = RecordingConfig(
        sample_rate=16_000,
        channels=1,
        output_dir=os.path.join("assets", "recordings"),
        output_filename="pipeline_v2_test.wav",
    )

    recorder = AudioRecorder(
        recording_config=rec_config,
        vad=vad,
        latency_tracker=tracker,
    )

    whisper = WhisperEngine(latency_tracker=tracker)
    gemini = GeminiClient(latency_tracker=tracker)
    
    piper = PiperEngine(latency_tracker=tracker)
    piper.initialize()
    
    player = TTSPlayer(latency_tracker=tracker)

    pipeline = Pipeline(
        whisper_engine=whisper,
        gemini_client=gemini,
        session=session,
        latency_tracker=tracker,
        piper_engine=piper,
        tts_player=player,
        memory_manager=memory,
    )

    # ── Step 2: Record ───────────────────────────────────────────────────
    print("\n--- Step 2: Speak now (pause to stop) ---\n")
    print("  Say something simple like 'Hello Nate, what is your name?'.")
    
    recording = recorder.record_until_silence(max_duration=15.0)

    if not recording:
        print("\n  [ERROR] Recording failed.")
        piper.shutdown()
        sys.exit(1)

    print(f"\n  Audio recorded: {recording.duration:.2f}s -> {recording.file_path}")

    # ── Step 3: Run pipeline loop ────────────────────────────────────────
    print("\n--- Step 3: Processing Pipeline (STT -> LLM -> TTS -> Playback) ---\n")
    response = pipeline.process_audio(recording)

    # ── Step 4: Display Results ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PIPELINE RESULTS")
    print("=" * 60)
    print(f"  User Query:          \"{memory.get_all_turns()[-2].text}\"")
    print(f"  Assistant Response:  \"{response.text}\"")
    print(f"  Current Memory Size: {memory.total_turns} turns")
    print(f"  Prompt Tokens:       {response.prompt_tokens}")
    print(f"  Response Tokens:     {response.response_tokens}")

    # ── Step 5: Latency Summary ──────────────────────────────────────────
    print("\n--- Step 5: Latency Summary ---")
    tracker.summary()

    # Clean up tts engine
    piper.shutdown()
    print("\n  Phase 6 integration test complete.\n")


if __name__ == "__main__":
    main()
