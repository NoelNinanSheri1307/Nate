"""
Audio recorder with Voice Activity Detection integration.

Provides configurable recording with automatic stop via Silero VAD,
fixed-duration recording, and thread-safe operation.
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import sounddevice as sd

from audio.vad import VoiceActivityDetector
from audio.audio_utils import save_audio
from audio.latency import LatencyTracker
from utils.logger import setup_logger
import config

logger = setup_logger("nate.audio.recorder")


@dataclass
class AudioRecording:
    """Result of a recording session.

    Contains both the raw audio samples for in-memory processing
    and the file path for debugging and playback.
    """

    samples: np.ndarray
    sample_rate: int
    duration: float
    file_path: str


@dataclass
class RecordingConfig:
    """Configuration for an audio recording session."""

    sample_rate: int = config.SAMPLE_RATE
    channels: int = config.CHANNELS
    block_size: int = config.BLOCK_SIZE
    output_dir: str = os.path.join("assets", "recordings")
    output_filename: str = "latest.wav"

    @property
    def output_path(self) -> str:
        return os.path.join(self.output_dir, self.output_filename)


class AudioRecorder:
    """Thread-safe audio recorder with VAD-based automatic stop.

    Supports both manual start/stop and fixed-duration recording.
    Integrates with VoiceActivityDetector for automatic end-of-speech detection.
    """

    def __init__(
        self,
        recording_config: RecordingConfig | None = None,
        vad: VoiceActivityDetector | None = None,
        latency_tracker: LatencyTracker | None = None,
    ) -> None:
        self._config = recording_config or RecordingConfig()
        self._vad = vad
        self._tracker = latency_tracker

        self._lock = threading.Lock()
        self._is_recording = False
        self._stop_event = threading.Event()
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

        os.makedirs(self._config.output_dir, exist_ok=True)

    @property
    def is_recording(self) -> bool:
        """Whether a recording is currently in progress."""
        return self._is_recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Sounddevice input stream callback.

        Appends audio chunks and checks VAD for end-of-speech.
        """
        if status:
            logger.warning("Audio callback status: %s", status)

        self._frames.append(indata.copy())

        # Check VAD for automatic stop
        if self._vad is not None:
            audio_chunk = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            should_stop = self._vad.process_chunk(audio_chunk, self._config.sample_rate)
            if should_stop:
                logger.info("VAD detected end of speech — stopping recording")
                self._stop_event.set()

    def start_recording(self) -> bool:
        """Begin recording from the default input device.

        Returns:
            True if recording started, False if already recording or on error.
        """
        with self._lock:
            if self._is_recording:
                logger.warning("Recording already in progress")
                return False

            self._frames.clear()
            self._stop_event.clear()

            if self._vad is not None:
                self._vad.reset()

            try:
                if self._tracker:
                    self._tracker.start_timer("recording_start")

                self._stream = sd.InputStream(
                    samplerate=self._config.sample_rate,
                    channels=self._config.channels,
                    blocksize=self._config.block_size,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._is_recording = True

                if self._tracker:
                    self._tracker.stop_timer("recording_start")

                logger.info("Recording started (rate=%d, channels=%d)",
                            self._config.sample_rate, self._config.channels)
                return True

            except Exception as exc:
                logger.error("Failed to start recording: %s", exc)
                self._is_recording = False
                return False

    def stop_recording(self) -> AudioRecording | None:
        """Stop the current recording and save to file.

        Returns:
            AudioRecording with samples and file path, or None on error.
        """
        with self._lock:
            if not self._is_recording:
                logger.warning("No recording in progress to stop")
                return None

            try:
                if self._tracker:
                    self._tracker.start_timer("recording_stop")

                if self._stream is not None:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None

                self._is_recording = False

                if not self._frames:
                    logger.warning("No audio frames captured")
                    return None

                audio_data = np.concatenate(self._frames, axis=0)
                output_path = self._config.output_path
                save_audio(output_path, audio_data, self._config.sample_rate)

                if self._tracker:
                    self._tracker.stop_timer("recording_stop")

                duration = len(audio_data) / self._config.sample_rate
                logger.info("Recording saved: %s (%.2fs)", output_path, duration)

                return AudioRecording(
                    samples=audio_data,
                    sample_rate=self._config.sample_rate,
                    duration=duration,
                    file_path=output_path,
                )

            except Exception as exc:
                logger.error("Failed to stop recording: %s", exc)
                self._is_recording = False
                return None

    def record_fixed_duration(self, seconds: float) -> AudioRecording | None:
        """Record for a fixed duration.

        Args:
            seconds: Duration to record in seconds.

        Returns:
            AudioRecording with samples and file path, or None on error.
        """
        logger.info("Recording for %.1f seconds...", seconds)

        if not self.start_recording():
            return None

        # Wait for either the duration to elapse or VAD to signal stop
        self._stop_event.wait(timeout=seconds)

        return self.stop_recording()

    def record_until_silence(self, max_duration: float = 30.0) -> AudioRecording | None:
        """Record until VAD detects end of speech or max duration is reached.

        Requires a VoiceActivityDetector to be configured.

        Args:
            max_duration: Maximum recording time in seconds (safety limit).

        Returns:
            AudioRecording with samples and file path, or None on error.
        """
        if self._vad is None:
            logger.error("VAD not configured — cannot record until silence")
            return None

        logger.info("Recording until silence (max %.1fs)...", max_duration)

        if not self.start_recording():
            return None

        # Wait for VAD stop signal or max duration
        self._stop_event.wait(timeout=max_duration)

        if not self._stop_event.is_set():
            logger.warning("Max duration reached without VAD stop signal")

        return self.stop_recording()
