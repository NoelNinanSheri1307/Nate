"""
Piper TTS Engine.

Coordinates the persistent background Piper process, providing low-latency,
reusable speech synthesis from text to WAV files.
"""

import os
import subprocess
import json
import time
import threading
from typing import Optional

from tts.models import TTSConfig
from tts.exceptions import TTSInitializationError, TTSSynthesisError
from audio.latency import LatencyTracker
from utils.logger import setup_logger

logger = setup_logger("nate.tts.piper")


class PiperEngine:
    """Persistent speech synthesis engine using Piper.

    Initializes the model once in a background subprocess, reusing it across
    requests via line-delimited JSON IPC on stdin/stdout to minimize latency.
    """

    def __init__(
        self,
        tts_config: Optional[TTSConfig] = None,
        latency_tracker: Optional[LatencyTracker] = None,
    ) -> None:
        self.config = tts_config or TTSConfig()
        self.tracker = latency_tracker
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """Start the background Piper subprocess and load the model.

        Raises:
            TTSInitializationError: If process fails to start or model files are missing.
        """
        with self._lock:
            if self._process is not None:
                logger.warning("Piper process already running.")
                return

            # Verification checks
            if not os.path.exists(self.config.executable_path):
                raise TTSInitializationError(
                    f"Piper executable not found at: {self.config.executable_path}"
                )
            if not os.path.exists(self.config.model_path):
                raise TTSInitializationError(
                    f"Piper voice model ONNX file not found at: {self.config.model_path}"
                )

            logger.info("Initializing Piper TTS (voice=%s)...", self.config.voice)
            
            if self.tracker:
                self.tracker.start_timer("tts_init")

            try:
                # Startup process in interactive JSON line mode
                cmd = [
                    self.config.executable_path,
                    "--model", self.config.model_path,
                    "--json-input"
                ]
                
                # Check for espeak-ng-data next to model
                espeak_data_path = os.path.join(os.path.dirname(self.config.executable_path), "espeak-ng-data")
                if os.path.exists(espeak_data_path):
                    cmd.extend(["--espeak_data", espeak_data_path])

                self._process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

                if self.tracker:
                    self.tracker.stop_timer("tts_init")

                logger.info("Piper TTS engine successfully initialized.")

            except Exception as exc:
                if self.tracker:
                    self.tracker.stop_timer("tts_init")
                self._process = None
                raise TTSInitializationError(f"Failed to launch Piper subprocess: {exc}") from exc

    def synthesize(self, text: str, output_path: Optional[str] = None) -> str:
        """Synthesize text to a WAV file.

        Args:
            text: Text to synthesize.
            output_path: Optional path to write output. If omitted, generates
                         a timestamped file in assets/recordings/.

        Returns:
            Absolute path to the synthesized WAV file.

        Raises:
            TTSSynthesisError: If synthesis fails.
        """
        if not text or not text.strip():
            raise TTSSynthesisError("Cannot synthesize empty or blank text.")

        with self._lock:
            if self._process is None or self._process.poll() is not None:
                logger.warning("Piper engine not running, attempting lazy initialization...")
                self.initialize()
                if self._process is None:
                    raise TTSSynthesisError("Piper process is not initialized and failed to start.")

            # Default output path generation
            if output_path is None:
                output_dir = os.path.join("assets", "recordings")
                os.makedirs(output_dir, exist_ok=True)
                timestamp = int(time.time() * 1000)
                output_path = os.path.join(output_dir, f"tts_{timestamp}.wav")

            # Resolve paths relative/absolute cleanly
            output_path_abs = os.path.abspath(output_path)
            
            logger.info("Synthesizing: '%s' -> %s", text, output_path_abs)

            if self.tracker:
                self.tracker.start_timer("tts_synthesis")

            try:
                # Prepare JSON request line
                payload = {
                    "text": text,
                    "output_file": output_path_abs
                }
                
                # Write to Piper stdin
                self._process.stdin.write(json.dumps(payload) + "\n")
                self._process.stdin.flush()

                # Read stdout for completion indicator (filename printed upon completion)
                while True:
                    line = self._process.stdout.readline()
                    if not line:
                        raise TTSSynthesisError("Piper subprocess closed unexpectedly.")
                    
                    cleaned_line = line.strip()
                    logger.debug("Piper process stdout: %s", cleaned_line)
                    
                    # When the matching file path is outputted, synthesis is finished
                    if cleaned_line == output_path_abs or os.path.basename(cleaned_line) == os.path.basename(output_path_abs):
                        break

                if self.tracker:
                    self.tracker.stop_timer("tts_synthesis")

                # Double check that file was written successfully
                if not os.path.exists(output_path_abs) or os.path.getsize(output_path_abs) == 0:
                    raise TTSSynthesisError("Piper finished but output WAV file is empty or missing.")

                logger.info("Speech synthesis completed successfully.")
                return output_path_abs

            except Exception as exc:
                if self.tracker:
                    self.tracker.stop_timer("tts_synthesis")
                logger.error("Synthesis failed: %s", exc)
                raise TTSSynthesisError(f"Piper synthesis loop failed: {exc}") from exc

    def shutdown(self) -> None:
        """Shutdown the background Piper subprocess cleanly."""
        with self._lock:
            if self._process is None:
                return

            logger.info("Shutting down Piper TTS engine subprocess...")
            try:
                if self._process.stdin:
                    self._process.stdin.close()
                if self._process.stdout:
                    self._process.stdout.close()
                if self._process.stderr:
                    self._process.stderr.close()
                
                # Wait for termination
                self._process.terminate()
                self._process.wait(timeout=2.0)
            except Exception as exc:
                logger.warning("Error closing Piper subprocess: %s", exc)
                try:
                    self._process.kill()
                except Exception:
                    pass
            finally:
                self._process = None
                logger.info("Piper TTS engine shutdown complete.")
