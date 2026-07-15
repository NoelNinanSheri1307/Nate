"""
Voice Activity Detection using Silero VAD.

Wraps the Silero VAD model with configurable thresholds and silence
timeout for end-of-speech detection. Designed for reuse across
recording and future STT pipelines.
"""

import time

import numpy as np
import torch

from utils.logger import setup_logger
import config

logger = setup_logger("nate.audio.vad")


class VoiceActivityDetector:
    """Silero VAD wrapper for speech/silence detection.

    Loads the Silero model once and processes audio chunks to determine
    whether the user is speaking or has finished speaking.
    """

    def __init__(
        self,
        threshold: float = config.VAD_THRESHOLD,
        silence_duration: float = config.SILENCE_DURATION,
    ) -> None:
        """Initialize the Voice Activity Detector.

        Args:
            threshold: Speech probability threshold (0.0 to 1.0).
                       Chunks above this are considered speech.
            silence_duration: Seconds of consecutive silence required
                              to signal end of speech.
        """
        self._threshold = threshold
        self._silence_duration = silence_duration

        # State tracking
        self._speech_detected = False
        self._silence_start: float | None = None

        # Load model
        self._model = self._load_model()

        logger.info("VAD initialized (threshold=%.2f, silence_timeout=%.1fs)",
                     self._threshold, self._silence_duration)

    def _load_model(self) -> torch.jit.ScriptModule:
        """Load the Silero VAD model.

        Returns:
            Loaded Silero VAD model.
        """
        try:
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            logger.info("Silero VAD model loaded successfully")
            return model
        except Exception as exc:
            logger.error("Failed to load Silero VAD model: %s", exc)
            raise

    def reset(self) -> None:
        """Reset the detector state for a new recording session."""
        self._speech_detected = False
        self._silence_start = None
        self._model.reset_states()
        logger.debug("VAD state reset")

    def get_speech_probability(
        self,
        audio_chunk: np.ndarray,
        sample_rate: int,
    ) -> float:
        """Compute speech probability for an audio chunk.

        Args:
            audio_chunk: 1D numpy array of float32 audio samples.
            sample_rate: Sample rate of the audio.

        Returns:
            Speech probability between 0.0 and 1.0.
        """
        tensor = torch.from_numpy(audio_chunk.astype(np.float32))
        if tensor.dim() > 1:
            tensor = tensor.squeeze()

        with torch.no_grad():
            probability = self._model(tensor, sample_rate).item()

        return probability

    def is_speech(self, audio_chunk: np.ndarray, sample_rate: int) -> bool:
        """Check if an audio chunk contains speech.

        Args:
            audio_chunk: 1D numpy array of audio samples.
            sample_rate: Sample rate of the audio.

        Returns:
            True if speech is detected above the threshold.
        """
        prob = self.get_speech_probability(audio_chunk, sample_rate)
        return prob >= self._threshold

    def process_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> bool:
        """Process an audio chunk and determine if recording should stop.

        Tracks speech onset and silence duration. Returns True when speech
        was detected and then silence exceeds the configured timeout.

        Args:
            audio_chunk: 1D numpy array of audio samples.
            sample_rate: Sample rate of the audio.

        Returns:
            True if recording should stop (end of speech detected).
        """
        prob = self.get_speech_probability(audio_chunk, sample_rate)
        is_speech = prob >= self._threshold
        now = time.monotonic()

        if is_speech:
            if not self._speech_detected:
                logger.debug("Speech started (prob=%.3f)", prob)
            self._speech_detected = True
            self._silence_start = None

        elif self._speech_detected:
            # Silence after speech
            if self._silence_start is None:
                self._silence_start = now
                logger.debug("Silence started (prob=%.3f)", prob)
            else:
                elapsed = now - self._silence_start
                if elapsed >= self._silence_duration:
                    logger.info("End of speech — %.2fs of silence (prob=%.3f)",
                                elapsed, prob)
                    return True

        return False

    @property
    def speech_detected(self) -> bool:
        """Whether speech has been detected in the current session."""
        return self._speech_detected

    @property
    def threshold(self) -> float:
        """Current speech probability threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Update the speech probability threshold."""
        self._threshold = max(0.0, min(1.0, value))
        logger.info("VAD threshold updated to %.2f", self._threshold)
