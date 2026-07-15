"""
Phase 2 — Audio Subsystem Integration Test.

Runs through the complete audio pipeline:
1. List devices
2. Select defaults
3. Record with VAD auto-stop
4. Save latest.wav
5. Play latest.wav
6. Print latency summary
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio.devices import (
    list_input_devices,
    list_output_devices,
    get_default_input,
    get_default_output,
)
from audio.recorder import AudioRecorder, RecordingConfig
from audio.player import AudioPlayer
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.test.audio", level="DEBUG")


def main() -> None:
    """Run the full audio subsystem test."""

    print("\n" + "=" * 60)
    print("  NATE — Phase 2 Audio Subsystem Test")
    print("=" * 60)

    # ── Step 1: List Devices ─────────────────────────────────────────────
    print("\n--- Step 1: Listing Audio Devices ---\n")

    inputs = list_input_devices()
    outputs = list_output_devices()

    print(f"\n  Microphones: {len(inputs)}")
    for dev in inputs:
        marker = " [DEFAULT]" if dev.is_default_input else ""
        print(f"    [{dev.index}] {dev.name}{marker}")

    print(f"\n  Speakers: {len(outputs)}")
    for dev in outputs:
        marker = " [DEFAULT]" if dev.is_default_output else ""
        print(f"    [{dev.index}] {dev.name}{marker}")

    # ── Step 2: Select Defaults ──────────────────────────────────────────
    print("\n--- Step 2: Selecting Default Devices ---\n")

    default_in = get_default_input()
    default_out = get_default_output()

    if default_in:
        print(f"  Default input:  [{default_in.index}] {default_in.name}")
    else:
        print("  No default input device found")
        return

    if default_out:
        print(f"  Default output: [{default_out.index}] {default_out.name}")
    else:
        print("  No default output device found")
        return

    # ── Setup Components ─────────────────────────────────────────────────
    tracker = LatencyTracker()

    print("\n--- Step 3: Loading VAD Model ---\n")
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

    player = AudioPlayer(
        sample_rate=16_000,
        latency_tracker=tracker,
    )

    # ── Step 3: Record with VAD ──────────────────────────────────────────
    print("\n--- Step 4: Recording (speak, then pause to auto-stop) ---\n")
    print("  Speak into your microphone. Recording will stop")
    print("  automatically after 1.5 seconds of silence.\n")

    saved_path = recorder.record_until_silence(max_duration=15.0)

    if not saved_path:
        print("\n  Recording failed or no audio captured.")
        return

    # ── Step 4: Save Confirmation ────────────────────────────────────────
    print(f"\n--- Step 5: Recording Saved ---")
    print(f"  File: {saved_path}")

    # ── Step 5: Playback ─────────────────────────────────────────────────
    print(f"\n--- Step 6: Playing Back Recording ---\n")

    success = player.play_file(saved_path)

    if success:
        player.wait_until_finished(timeout=30.0)
        print("  Playback complete.")
    else:
        print("  Playback failed.")

    # ── Step 6: Latency Summary ──────────────────────────────────────────
    print("\n--- Step 7: Latency Summary ---")
    tracker.summary()

    print("\n  Phase 2 audio test complete.\n")


if __name__ == "__main__":
    main()
