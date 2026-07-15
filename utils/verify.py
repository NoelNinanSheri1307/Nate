"""
Dependency verification utility for Nate AI Assistant.

Checks that all required libraries are importable and
detects available audio input/output devices.
"""

import importlib
import sys


# ─── Required Libraries ─────────────────────────────────────────────────────

REQUIRED_LIBRARIES: list[tuple[str, str]] = [
    ("torch",          "PyTorch"),
    ("faster_whisper",  "Faster Whisper"),
    ("sounddevice",     "sounddevice"),
    ("soundfile",       "SoundFile"),
    ("silero_vad",      "Silero VAD"),
    ("google.genai",    "Google GenAI"),
    ("dotenv",          "python-dotenv"),
]


def verify_imports() -> tuple[list[str], list[str]]:
    """Verify that all required Python packages can be imported.

    Returns:
        A tuple of (successful_imports, failed_imports) as display names.
    """
    passed: list[str] = []
    failed: list[str] = []

    for module_name, display_name in REQUIRED_LIBRARIES:
        try:
            importlib.import_module(module_name)
            passed.append(display_name)
        except ImportError:
            failed.append(display_name)

    return passed, failed


def detect_audio_devices() -> dict[str, list[dict]]:
    """Detect available audio input and output devices.

    Returns:
        Dictionary with 'inputs' and 'outputs' lists,
        each containing device info dicts with 'index' and 'name'.
    """
    devices: dict[str, list[dict]] = {"inputs": [], "outputs": []}

    try:
        import sounddevice as sd

        device_list = sd.query_devices()
        for i, dev in enumerate(device_list):
            info = {"index": i, "name": dev["name"]}
            if dev["max_input_channels"] > 0:
                devices["inputs"].append(info)
            if dev["max_output_channels"] > 0:
                devices["outputs"].append(info)

    except Exception as e:
        print(f"  [WARN] Could not query audio devices: {e}", file=sys.stderr)

    return devices


def run_verification() -> bool:
    """Run full dependency and device verification.

    Prints a formatted report to stdout.

    Returns:
        True if all checks passed, False otherwise.
    """
    print("\n" + "=" * 60)
    print("  NATE — Dependency Verification")
    print("=" * 60)

    # ── Library Checks ───────────────────────────────────────────────────
    passed, failed = verify_imports()

    print("\n  Library Checks")
    print("  " + "-" * 40)

    for name in passed:
        print(f"    ✓  {name}")

    for name in failed:
        print(f"    ✗  {name}")

    # ── Audio Devices ────────────────────────────────────────────────────
    print("\n  Audio Devices")
    print("  " + "-" * 40)

    devices = detect_audio_devices()

    if devices["inputs"]:
        print(f"    Microphones ({len(devices['inputs'])} found):")
        for dev in devices["inputs"]:
            print(f"      [{dev['index']}] {dev['name']}")
    else:
        print("    ✗  No microphones detected")

    if devices["outputs"]:
        print(f"    Speakers ({len(devices['outputs'])} found):")
        for dev in devices["outputs"]:
            print(f"      [{dev['index']}] {dev['name']}")
    else:
        print("    ✗  No speakers detected")

    # ── Summary ──────────────────────────────────────────────────────────
    all_ok = len(failed) == 0
    print("\n" + "=" * 60)

    if all_ok:
        print("  ✓  All dependencies verified successfully.")
    else:
        print(f"  ✗  {len(failed)} missing: {', '.join(failed)}")
        print("     Run: pip install -r requirements.txt")

    print("=" * 60 + "\n")
    return all_ok


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
