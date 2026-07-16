"""
TTS audio playback wrapper using the existing AudioPlayer.
"""

from typing import Optional
from audio.player import AudioPlayer
from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.tts.player")


class TTSPlayer:
    """Wrapper around the project's AudioPlayer to handle TTS speech playback.

    Provides support for blocking playback, audio interruption, and latency tracking.
    """

    def __init__(self, latency_tracker: Optional[LatencyTracker] = None) -> None:
        self._player = AudioPlayer(sample_rate=22050, latency_tracker=latency_tracker)
        self.tracker = latency_tracker

    def play(self, wav_path: str, blocking: bool = True) -> bool:
        """Play a synthesized speech WAV file.

        Args:
            wav_path: Path to the WAV file.
            blocking: If True, blocks execution until audio finishes playing.

        Returns:
            True if playback succeeded, False otherwise.
        """
        logger.info("Playing speech: %s (blocking=%s)", wav_path, blocking)
        
        # Start playback
        success = self._player.play_file(wav_path)
        if not success:
            logger.error("Failed to play speech audio file: %s", wav_path)
            return False

        if blocking:
            logger.debug("Blocking on speech playback...")
            self._player.wait_until_finished()
            logger.debug("Speech playback complete.")

        return True

    def stop(self) -> None:
        """Interrupt and stop current playback."""
        logger.info("Interrupting speech playback.")
        self._player.stop()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until current playback completes.

        Args:
            timeout: Max time to wait in seconds.

        Returns:
            True if playback finished, False if timeout expired.
        """
        return self._player.wait_until_finished(timeout=timeout)
