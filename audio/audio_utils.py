"""
Audio utility functions.

Provides common operations for saving, loading, normalizing,
resampling, and validating audio data.
"""

import os

import numpy as np
import soundfile as sf

from utils.logger import setup_logger

logger = setup_logger("nate.audio.utils")


def save_audio(path: str, audio_data: np.ndarray, sample_rate: int) -> bool:
    """Save audio data to a WAV file.

    Args:
        path: Output file path.
        audio_data: Audio samples as a numpy array.
        sample_rate: Sample rate in Hz.

    Returns:
        True if saved successfully, False on error.
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        sf.write(path, audio_data, sample_rate)
        logger.info("Saved audio to %s (%d samples, %d Hz)",
                     path, len(audio_data), sample_rate)
        return True
    except Exception as exc:
        logger.error("Failed to save audio to %s: %s", path, exc)
        return False


def load_audio(path: str) -> tuple[np.ndarray, int] | None:
    """Load audio from a file.

    Args:
        path: Path to the audio file.

    Returns:
        Tuple of (audio_data, sample_rate), or None on error.
    """
    if not os.path.isfile(path):
        logger.error("Audio file not found: %s", path)
        return None

    try:
        data, rate = sf.read(path, dtype="float32")
        logger.info("Loaded audio from %s (%d samples, %d Hz)",
                     path, len(data), rate)
        return data, rate
    except Exception as exc:
        logger.error("Failed to load audio from %s: %s", path, exc)
        return None


def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """Normalize audio to the range [-1.0, 1.0].

    Args:
        audio_data: Audio samples as a numpy array.

    Returns:
        Normalized audio array.
    """
    peak = np.max(np.abs(audio_data))
    if peak == 0:
        logger.warning("Audio is silent — skipping normalization")
        return audio_data

    normalized = audio_data / peak
    logger.debug("Normalized audio (peak=%.6f)", peak)
    return normalized


def convert_to_mono(audio_data: np.ndarray) -> np.ndarray:
    """Convert multi-channel audio to mono by averaging channels.

    Args:
        audio_data: Audio samples, shape (samples,) or (samples, channels).

    Returns:
        Mono audio array with shape (samples,).
    """
    if audio_data.ndim == 1:
        return audio_data

    if audio_data.ndim == 2 and audio_data.shape[1] == 1:
        return audio_data.flatten()

    mono = np.mean(audio_data, axis=1)
    logger.debug("Converted %d-channel audio to mono", audio_data.shape[1])
    return mono


def resample_audio(
    audio_data: np.ndarray,
    original_rate: int,
    target_rate: int,
) -> np.ndarray:
    """Resample audio to a target sample rate using linear interpolation.

    For production use, consider using a higher-quality resampler.

    Args:
        audio_data: 1D audio samples.
        original_rate: Original sample rate in Hz.
        target_rate: Target sample rate in Hz.

    Returns:
        Resampled audio array.
    """
    if original_rate == target_rate:
        return audio_data

    duration = len(audio_data) / original_rate
    target_length = int(duration * target_rate)
    indices = np.linspace(0, len(audio_data) - 1, target_length)
    resampled = np.interp(indices, np.arange(len(audio_data)), audio_data)

    logger.debug("Resampled audio from %d Hz to %d Hz (%d -> %d samples)",
                  original_rate, target_rate, len(audio_data), len(resampled))
    return resampled.astype(audio_data.dtype)


def validate_audio(
    audio_data: np.ndarray,
    sample_rate: int,
    min_duration: float = 0.1,
    max_duration: float = 300.0,
) -> tuple[bool, str]:
    """Validate audio data for basic sanity checks.

    Args:
        audio_data: Audio samples as a numpy array.
        sample_rate: Sample rate in Hz.
        min_duration: Minimum acceptable duration in seconds.
        max_duration: Maximum acceptable duration in seconds.

    Returns:
        Tuple of (is_valid, message).
    """
    if audio_data is None or len(audio_data) == 0:
        return False, "Audio data is empty"

    duration = len(audio_data) / sample_rate

    if duration < min_duration:
        return False, f"Audio too short: {duration:.3f}s (min {min_duration}s)"

    if duration > max_duration:
        return False, f"Audio too long: {duration:.1f}s (max {max_duration}s)"

    if np.all(audio_data == 0):
        return False, "Audio is completely silent (all zeros)"

    if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
        return False, "Audio contains NaN or Inf values"

    logger.debug("Audio validated: %.2fs, rate=%d, shape=%s",
                  duration, sample_rate, audio_data.shape)
    return True, f"Valid audio: {duration:.2f}s"
