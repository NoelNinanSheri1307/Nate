"""
Faster-Whisper speech-to-text engine.

Provides a lazy-loaded, reusable Whisper model that automatically
selects CUDA (float16) or CPU (int8) based on availability.
Supports transcription from both file paths and in-memory numpy arrays.
"""

import time
import io

import numpy as np
import soundfile as sf
import torch
from faster_whisper import WhisperModel

from stt.transcript import Transcript
from stt.language import get_language_name
from audio.latency import LatencyTracker
from utils.logger import setup_logger
import config

logger = setup_logger("nate.stt.whisper")


class WhisperEngine:
    """Lazy-loaded Faster-Whisper transcription engine.

    The model is loaded on first use and reused for subsequent calls.
    Automatically selects the best available compute device.
    """

    def __init__(
        self,
        model_size: str = config.STT_MODEL_SIZE,
        beam_size: int = config.STT_BEAM_SIZE,
        latency_tracker: LatencyTracker | None = None,
    ) -> None:
        """Initialize the Whisper engine.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3).
            beam_size: Beam size for decoding.
            latency_tracker: Optional latency tracker for measurements.
        """
        self._model_size = model_size
        self._beam_size = beam_size
        self._tracker = latency_tracker

        self._model: WhisperModel | None = None
        self._device: str = ""
        self._compute_type: str = ""

        logger.info("WhisperEngine initialized (model=%s, beam_size=%d)",
                     self._model_size, self._beam_size)

    def _detect_device(self) -> tuple[str, str]:
        """Detect the best available compute device.

        Returns:
            Tuple of (device, compute_type).
        """
        if torch.cuda.is_available():
            logger.info("CUDA available — using GPU with float16")
            return "cuda", "float16"
        else:
            logger.info("CUDA not available — using CPU with int8")
            return "cpu", "int8"

    def _ensure_model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first use.

        Returns:
            Loaded WhisperModel instance.

        Raises:
            RuntimeError: If model loading fails.
        """
        if self._model is not None:
            return self._model

        self._device, self._compute_type = self._detect_device()

        logger.info("Loading Faster-Whisper model '%s' on %s (%s)...",
                     self._model_size, self._device, self._compute_type)

        try:
            if self._tracker:
                self._tracker.start_timer("model_load")

            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )

            if self._tracker:
                self._tracker.stop_timer("model_load")

        except Exception as exc:
            if self._device == "cuda":
                logger.warning("Failed to load Whisper model on CUDA: %s. Falling back to CPU.", exc)
                self._device = "cpu"
                self._compute_type = "int8"
                logger.info("Loading Faster-Whisper model '%s' on CPU (int8)...", self._model_size)
                try:
                    self._model = WhisperModel(
                        self._model_size,
                        device=self._device,
                        compute_type=self._compute_type,
                    )
                    if self._tracker:
                        self._tracker.stop_timer("model_load")
                except Exception as cpu_exc:
                    logger.error("Failed to load Whisper model on CPU fallback: %s", cpu_exc)
                    if self._tracker:
                        self._tracker.stop_timer("model_load")
                    raise RuntimeError(f"Whisper model loading failed on both GPU and CPU: {cpu_exc}") from cpu_exc
            else:
                logger.error("Failed to load Whisper model: %s", exc)
                if self._tracker:
                    self._tracker.stop_timer("model_load")
                raise RuntimeError(f"Whisper model loading failed: {exc}") from exc

        # Clearly display selected model configuration on success
        logger.info("Whisper model : %s", self._model_size)
        logger.info("Device        : %s", self._device.upper())
        logger.info("Compute Type  : %s", self._compute_type)
        logger.info("Whisper model loaded successfully")
        return self._model

    def transcribe_file(self, file_path: str) -> Transcript | None:
        """Transcribe audio from a file.

        Args:
            file_path: Path to a WAV audio file.

        Returns:
            Transcript with results, or None on error.
        """
        logger.info("Transcribing file: %s", file_path)
        return self._transcribe(file_path)

    def transcribe_array(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
    ) -> Transcript | None:
        """Transcribe audio from an in-memory numpy array.

        Args:
            audio_data: Audio samples as a float32 numpy array.
            sample_rate: Sample rate of the audio.

        Returns:
            Transcript with results, or None on error.
        """
        duration = len(audio_data) / sample_rate
        logger.info("Transcribing in-memory audio (%.2fs, %d Hz)", duration, sample_rate)

        # Ensure mono float32
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]
        audio_data = audio_data.astype(np.float32)

        return self._transcribe(audio_data)

    def _transcribe(self, source: str | np.ndarray) -> Transcript | None:
        """Internal transcription logic for both file and array sources.

        Args:
            source: File path string or numpy array of audio samples.

        Returns:
            Transcript with results, or None on error.
        """
        try:
            model = self._ensure_model()
        except RuntimeError:
            return None

        # Compute audio duration for the result
        if isinstance(source, str):
            try:
                data, rate = sf.read(source, dtype="float32")
                audio_duration = len(data) / rate
            except Exception as exc:
                logger.error("Failed to read audio file for duration: %s", exc)
                return None
        else:
            if len(source) == 0:
                logger.warning("Empty audio data — skipping transcription")
                return None
            # Estimate duration (will be corrected from segments if available)
            audio_duration = 0.0

        logger.info("Transcription started...")

        if self._tracker:
            self._tracker.start_timer("transcription")

        start_time = time.perf_counter()

        try:
            segments, info = model.transcribe(
                source,
                beam_size=self._beam_size,
                vad_filter=False,  # We use our own VAD
            )

            # Collect all segment text
            text_parts: list[str] = []
            for segment in segments:
                text_parts.append(segment.text)

            text = " ".join(text_parts).strip()
            processing_time = time.perf_counter() - start_time

            if self._tracker:
                self._tracker.stop_timer("transcription")

            # Use duration from info if available, otherwise from audio
            detected_duration = info.duration if info.duration > 0 else audio_duration

            # Estimate confidence from log probability if available
            confidence = self._estimate_confidence(info)

            language = info.language or "unknown"

            transcript = Transcript(
                text=text,
                language=language,
                confidence=confidence,
                duration=detected_duration,
                processing_time=processing_time,
            )

            logger.info("Transcription complete in %.3fs", processing_time)
            logger.info("Language: %s (%s)", language, get_language_name(language))
            logger.info("Text: %s", text if text else "(empty)")

            return transcript

        except Exception as exc:
            logger.error("Transcription failed: %s", exc)
            if self._tracker:
                self._tracker.stop_timer("transcription")
            return None

    @staticmethod
    def _estimate_confidence(info) -> float:
        """Estimate a confidence score from Whisper's detection info.

        Args:
            info: TranscriptionInfo from Faster-Whisper.

        Returns:
            Estimated confidence between 0.0 and 1.0.
        """
        # language_probability is the best proxy for confidence
        if hasattr(info, "language_probability") and info.language_probability:
            return min(1.0, max(0.0, info.language_probability))
        return 0.0

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded."""
        return self._model is not None

    @property
    def device(self) -> str:
        """The compute device in use (cuda or cpu)."""
        return self._device

    @property
    def model_size(self) -> str:
        """The configured model size."""
        return self._model_size
