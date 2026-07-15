"""
Phase 3 — Speech-to-Text Integration Test.

Records speech using the existing recorder and VAD,
then transcribes with Faster-Whisper and prints results.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio.recorder import AudioRecorder, RecordingConfig
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker
from stt.whisper_engine import WhisperEngine
from stt.language import get_language_name
from utils.logger import setup_logger

logger = setup_logger("nate.test.stt", level="DEBUG")


def main() -> None:
    """Run the speech-to-text integration test."""

    print("\n" + "=" * 60)
    print("  NATE — Phase 3 Speech-to-Text Test")
    print("=" * 60)

    tracker = LatencyTracker()

    # ── Step 1: Setup Components ─────────────────────────────────────────
    print("\n--- Step 1: Loading Models ---\n")

    vad = VoiceActivityDetector(threshold=0.5, silence_duration=1.5)

    rec_config = RecordingConfig(
        sample_rate=16_000,
        channels=1,
        output_dir=os.path.join("assets", "recordings"),
        output_filename="latest.wav",
    )

    recorder = AudioRecorder(
        recording_config=rec_config,
        vad=vad,
        latency_tracker=tracker,
    )

    whisper = WhisperEngine(latency_tracker=tracker)

    # ── Step 2: Record ───────────────────────────────────────────────────
    print("\n--- Step 2: Recording ---\n")
    print("  Speak into your microphone. Recording will stop")
    print("  automatically after 1.5 seconds of silence.\n")

    recording = recorder.record_until_silence(max_duration=15.0)

    if not recording:
        print("\n  Recording failed or no audio captured.")
        return

    print(f"\n  Recorded {recording.duration:.2f}s -> {recording.file_path}")

    # ── Step 3: Transcribe ───────────────────────────────────────────────
    print("\n--- Step 3: Transcribing ---\n")

    # Transcribe from memory (faster, no disk re-read)
    transcript = whisper.transcribe_array(recording.samples, recording.sample_rate)

    if not transcript:
        print("\n  Transcription failed.")
        return

    # ── Step 4: Results ──────────────────────────────────────────────────
    print("\n--- Step 4: Results ---\n")
    print(f"  Transcript:       \"{transcript.text}\"")
    print(f"  Language:         {transcript.language} ({get_language_name(transcript.language)})")
    print(f"  Confidence:       {transcript.confidence:.2f}")
    print(f"  Audio duration:   {transcript.duration:.2f}s")
    print(f"  Processing time:  {transcript.processing_time:.3f}s")

    # ── Step 5: Latency Summary ──────────────────────────────────────────
    print("\n--- Step 5: Latency Summary ---")
    tracker.summary()

    print("\n  Phase 3 STT test complete.\n")


if __name__ == "__main__":
    main()
