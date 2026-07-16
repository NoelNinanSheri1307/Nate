"""
Wake Word Detector using OpenWakeWord.

Provides continuous background listening for the "Hey Nate" wake phrase
using a lightweight, CPU-friendly model with zero audio gaps.
"""

import time
import threading
import queue
import numpy as np
from dataclasses import dataclass
from typing import Optional, List

from utils.logger import setup_logger

logger = setup_logger("nate.wakeword.detector")


@dataclass
class WakeWordResult:
    """Result from a successful wake word detection."""
    keyword: str
    confidence: float
    timestamp: float


class WakeWordDetector:
    """OpenWakeWord-based wake word detector for 'Hey Nate'.

    Uses openwakeword library with pre-trained models for Mycroft/Jarvis
    to detect custom wake phrases continuously with zero audio gaps.
    """

    def __init__(
        self,
        wakeword_models: Optional[List[str]] = None,
        threshold: float = 0.4,  # slightly lowered threshold to match "Hey Nate" phonetics
        sample_rate: int = 16000,
        chunk_size: int = 1280,
    ) -> None:
        """Initialize the wake word detector.

        Args:
            wakeword_models: List of openwakeword model names to load.
            threshold: Minimum confidence score to trigger detection.
            sample_rate: Audio sample rate for microphone input.
            chunk_size: Number of audio frames per detection chunk.
        """
        self.models_list = wakeword_models or ["hey_jarvis", "hey_mycroft"]
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        self._model = None
        self._audio_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._detected_result: Optional[WakeWordResult] = None
        self._thread: Optional[threading.Thread] = None
        self._stream = None
        self._lock = threading.Lock()

        try:
            import openwakeword
            from openwakeword.model import Model
            
            # Download default models if not present
            openwakeword.utils.download_models()
            
            self._model = Model(
                wakeword_models=self.models_list,
                inference_framework="onnx"
            )
            logger.info("OpenWakeWord model loaded: %s (threshold=%.2f)", self.models_list, threshold)
            
        except ImportError:
            logger.error("openwakeword package not installed.")
            raise
        except Exception as exc:
            logger.error("Failed to initialize OpenWakeWord: %s", exc)
            raise

    def start(self) -> None:
        """Start the continuous background recording and detection stream."""
        with self._lock:
            if self._stream is not None:
                return

            self._stop_event.clear()
            self._detected_result = None
            
            # Clear any stale audio items in the queue
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break

            try:
                import sounddevice as sd

                def audio_callback(indata, frames, time_info, status):
                    if status:
                        logger.warning("Sounddevice status: %s", status)
                    self._audio_queue.put(indata.copy())

                # Open the stream with 1280 blocksize (80ms chunks at 16kHz)
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='int16',
                    blocksize=self.chunk_size,
                    callback=audio_callback
                )
                self._stream.start()

                self._thread = threading.Thread(target=self._process_loop, daemon=True)
                self._thread.start()
                logger.info("Wake word detector background stream started.")

            except Exception as exc:
                logger.error("Failed to start sounddevice stream: %s", exc)
                self._stream = None

    def stop(self) -> None:
        """Stop background stream and processing thread to release audio devices."""
        with self._lock:
            self._stop_event.set()
            
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as exc:
                    logger.debug("Error closing stream: %s", exc)
                self._stream = None

            if self._thread:
                self._thread.join(timeout=2.0)
                self._thread = None
                
            logger.info("Wake word detector background stream stopped.")

    def _process_loop(self) -> None:
        """Background loop consuming chunks and performing inference."""
        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._model is None:
                continue

            try:
                # Flatten chunk to 1D array
                audio_flat = chunk.flatten()
                
                # Perform inference
                prediction = self._model.predict(audio_flat)
                
                for model_name, score in prediction.items():
                    if score >= self.threshold:
                        logger.info("Wake word match: %s (score=%.3f)", model_name, score)
                        self._detected_result = WakeWordResult(
                            keyword="Hey Nate",
                            confidence=float(score),
                            timestamp=time.time()
                        )
            except Exception as exc:
                logger.error("Error in wake word inference: %s", exc)

    def listen_once(self, timeout: float = 0.5) -> Optional[WakeWordResult]:
        """Check for a wake word detection event within a short polling window.

        Args:
            timeout: Max time to poll for detection.

        Returns:
            WakeWordResult if detected, None otherwise.
        """
        start_time = time.perf_counter()
        while (time.perf_counter() - start_time) < timeout:
            if self._detected_result is not None:
                result = self._detected_result
                self._detected_result = None  # Reset trigger
                return result
            time.sleep(0.02)
        return None
