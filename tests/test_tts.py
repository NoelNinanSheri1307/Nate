"""
Phase 5 — Text-to-Speech Subsystem Test.

Tests PiperEngine initialization, speech synthesis, and audio playback.
Logs synthesis and playback latencies.
"""

import sys
import os

# Ensure project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts.piper_engine import PiperEngine
from tts.player import TTSPlayer
from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.test.tts", level="INFO")


def main() -> None:
    """Run the TTS subsystem test."""
    print("\n" + "=" * 60)
    print("  NATE — Phase 5 Text-to-Speech Test")
    print("=" * 60)

    tracker = LatencyTracker()

    # ── Step 1: Initialize Piper ─────────────────────────────────────────
    print("\n--- Step 1: Initializing Piper TTS Engine ---\n")
    engine = PiperEngine(latency_tracker=tracker)
    
    try:
        engine.initialize()
    except Exception as exc:
        print(f"  [ERROR] Failed to initialize Piper: {exc}")
        sys.exit(1)

    player = TTSPlayer(latency_tracker=tracker)

    # ── Step 2: Synthesize Speech ────────────────────────────────────────
    print("\n--- Step 2: Synthesizing Speech ---\n")
    text = "Hello! I am Nate, your real-time voice assistant. Text-to-speech is fully functional."
    
    try:
        wav_path = engine.synthesize(text)
        print(f"  Successfully synthesized: '{text}'")
        print(f"  Saved to: {wav_path}")
    except Exception as exc:
        print(f"  [ERROR] Synthesis failed: {exc}")
        engine.shutdown()
        sys.exit(1)

    # ── Step 3: Play Speech ──────────────────────────────────────────────
    print("\n--- Step 3: Playing Back Speech ---\n")
    success = player.play(wav_path, blocking=True)

    if success:
        print("  Playback complete.")
    else:
        print("  Playback failed.")

    # ── Step 4: Latency Report ───────────────────────────────────────────
    print("\n--- Step 4: Latency Report ---")
    tracker.summary()

    # Shutdown engine
    engine.shutdown()
    print("\n  Phase 5 TTS test complete.\n")


if __name__ == "__main__":
    main()
