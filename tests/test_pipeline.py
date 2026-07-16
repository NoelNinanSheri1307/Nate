"""
Phase 4 — Pipeline Orchestrator Integration Test.

Performs a full pass:
1. Records audio from microphone with Silero VAD auto-stop.
2. Runs the AudioRecording through the Pipeline (Whisper STT + Gemini LLM).
3. Prints the transcribed input, assistant response, and latency tracking results.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from audio.recorder import AudioRecorder, RecordingConfig
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker
from stt.whisper_engine import WhisperEngine
from llm.gemini_client import GeminiClient
from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from orchestrator.session import ConversationSession
from orchestrator.pipeline import Pipeline
from orchestrator.events import PipelineEvent
from utils.logger import setup_logger

logger = setup_logger("nate.test.pipeline", level="DEBUG")


def main() -> None:
    """Run the pipeline integration test."""
    print("\n" + "=" * 60)
    print("  NATE — Phase 5 Pipeline Orchestrator Test")
    print("=" * 60)

    # ── Verify config ────────────────────────────────────────────────────
    if not config.validate_config():
        print("  [ERROR] Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
        sys.exit(1)

    tracker = LatencyTracker()
    session = ConversationSession()

    # Define a clean event handler to log events as they flow through the pipeline
    def event_logger(event: PipelineEvent) -> None:
        logger.info("[EVENT] Raised event: %s", event.__class__.__name__)

    session.register_listener(event_logger)

    print("\n--- Step 1: Loading Whisper, VAD & Piper Models ---\n")
    vad = VoiceActivityDetector(threshold=0.5, silence_duration=1.5)
    
    rec_config = RecordingConfig(
        sample_rate=16_000,
        channels=1,
        output_dir=os.path.join("assets", "recordings"),
        output_filename="pipeline_test.wav",
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
    )

    # ── Step 2: Record ───────────────────────────────────────────────────
    print("\n--- Step 2: Recording (speak, then pause to auto-stop) ---\n")
    print("  Speak into your microphone. Say something simple like 'Hello Nate'.")
    print("  Recording will stop automatically after 1.5 seconds of silence.\n")

    recording = recorder.record_until_silence(max_duration=15.0)

    if not recording:
        print("\n  [ERROR] Recording failed or no audio captured.")
        sys.exit(1)

    print(f"\n  Audio recorded: {recording.duration:.2f}s -> {recording.file_path}")

    # ── Step 3: Run Orchestrator Pipeline ────────────────────────────────
    print("\n--- Step 3: Running Pipeline (STT -> LLM) ---\n")

    response = pipeline.process_audio(recording)

    # ── Step 4: Display Results ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    
    # Get last items in history
    history = session.get_history()
    user_query = next((h["text"] for h in reversed(history) if h["role"] == "user"), "(No transcript)")
    
    print(f"  User Query:         \"{user_query}\"")
    print(f"  Assistant Response: \"{response.text}\"")
    print(f"  Tokens Used:        Prompt: {response.prompt_tokens} | Response: {response.response_tokens}")
    print(f"  LLM Latency:        {response.latency_ms:.2f} ms")

    # ── Step 5: Latency Summary ──────────────────────────────────────────
    print("\n--- Step 5: Latency Summary ---")
    tracker.summary()

    # Clean up tts engine
    piper.shutdown()
    print("\n  Phase 5 integration test complete.\n")


if __name__ == "__main__":
    main()
