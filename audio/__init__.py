"""
Audio subsystem for Nate AI Assistant.

Provides microphone capture, playback, voice activity detection,
audio utilities, and latency measurement.
"""

from audio.devices import (
    list_input_devices,
    list_output_devices,
    get_default_input,
    get_default_output,
)
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from audio.vad import VoiceActivityDetector
from audio.latency import LatencyTracker

__all__ = [
    "list_input_devices",
    "list_output_devices",
    "get_default_input",
    "get_default_output",
    "AudioRecorder",
    "AudioPlayer",
    "VoiceActivityDetector",
    "LatencyTracker",
]
