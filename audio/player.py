"""
Audio playback module.

Provides file and array playback with blocking/non-blocking modes
and graceful error handling.
"""

import os
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf

from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.audio.player")


class AudioPlayer:
    """Audio player with file and array playback support.

    Handles missing files, busy devices, and provides both
    blocking and non-blocking playback.
    """

    def __init__(
        self,
        sample_rate: int = 16_000,
        latency_tracker: LatencyTracker | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._tracker = latency_tracker
        self._lock = threading.Lock()
        self._is_playing = False
        self._playback_finished = threading.Event()
        self._playback_finished.set()  # Not playing initially

    @property
    def is_playing(self) -> bool:
        """Whether audio is currently being played."""
        return self._is_playing

    def play(self, audio_data: np.ndarray, sample_rate: int | None = None) -> bool:
        """Play audio from a numpy array (non-blocking).

        Args:
            audio_data: Audio samples as a numpy array.
            sample_rate: Sample rate. Uses default if not provided.

        Returns:
            True if playback started, False on error.
        """
        with self._lock:
            if self._is_playing:
                logger.warning("Playback already in progress")
                return False

        rate = sample_rate or self._sample_rate

        try:
            self._is_playing = True
            self._playback_finished.clear()

            def _finished_callback() -> None:
                self._is_playing = False
                self._playback_finished.set()
                logger.debug("Playback finished")

            # Measure only the latency to initiate playback, not duration
            if self._tracker:
                self._tracker.start_timer("playback")

            sd.play(audio_data, samplerate=rate)

            if self._tracker:
                self._tracker.stop_timer("playback")

            # Monitor completion in a background thread
            def _monitor() -> None:
                sd.wait()
                _finished_callback()

            threading.Thread(target=_monitor, daemon=True).start()

            duration = len(audio_data) / rate
            logger.info("Playing audio (%.2fs at %d Hz)", duration, rate)
            return True

        except Exception as exc:
            logger.error("Playback failed: %s", exc)
            self._is_playing = False
            self._playback_finished.set()
            return False

    def play_file(self, path: str) -> bool:
        """Play audio from a WAV file.

        Args:
            path: Path to the audio file.

        Returns:
            True if playback started, False on error.
        """
        if not os.path.isfile(path):
            logger.error("Audio file not found: %s", path)
            return False

        try:
            data, rate = sf.read(path, dtype="float32")
            logger.info("Loaded %s (%d samples, %d Hz)", path, len(data), rate)
            return self.play(data, sample_rate=rate)

        except Exception as exc:
            logger.error("Failed to load audio file %s: %s", path, exc)
            return False

    def stop(self) -> None:
        """Stop any current playback."""
        try:
            sd.stop()
            self._is_playing = False
            self._playback_finished.set()
            logger.info("Playback stopped")
        except Exception as exc:
            logger.error("Error stopping playback: %s", exc)

    def wait_until_finished(self, timeout: float | None = None) -> bool:
        """Block until the current playback finishes.

        Args:
            timeout: Maximum time to wait in seconds. None for unlimited.

        Returns:
            True if playback finished, False if timed out.
        """
        finished = self._playback_finished.wait(timeout=timeout)
        if not finished:
            logger.warning("Playback wait timed out after %.1fs", timeout)
        return finished
