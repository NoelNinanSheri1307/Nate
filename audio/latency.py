"""
Latency tracking for the audio pipeline.

Measures timing of recording start/stop, VAD processing,
and playback operations using monotonic timers.
"""

import time
from dataclasses import dataclass, field

from utils.logger import setup_logger

logger = setup_logger("nate.audio.latency")


@dataclass
class TimerRecord:
    """A single timing measurement."""

    label: str
    start_time: float = 0.0
    end_time: float = 0.0
    elapsed_ms: float = 0.0


class LatencyTracker:
    """Tracks latency across pipeline stages.

    Provides named timers for measuring individual operations
    and a summary report of all measurements.
    """

    def __init__(self) -> None:
        self._timers: dict[str, TimerRecord] = {}
        self._active_starts: dict[str, float] = {}

    def start_timer(self, label: str) -> None:
        """Start a named timer.

        Args:
            label: Identifier for this measurement (e.g. "recording_start").
        """
        self._active_starts[label] = time.perf_counter()
        logger.debug("Timer started: %s", label)

    def stop_timer(self, label: str) -> float:
        """Stop a named timer and record the elapsed time.

        Args:
            label: Identifier matching a previous start_timer call.

        Returns:
            Elapsed time in milliseconds, or -1 if the timer was not started.
        """
        end = time.perf_counter()
        start = self._active_starts.pop(label, None)

        if start is None:
            logger.warning("Timer '%s' was never started", label)
            return -1.0

        elapsed_ms = (end - start) * 1000.0
        self._timers[label] = TimerRecord(
            label=label,
            start_time=start,
            end_time=end,
            elapsed_ms=elapsed_ms,
        )

        logger.debug("Timer stopped: %s = %.2f ms", label, elapsed_ms)
        return elapsed_ms

    def get_elapsed(self, label: str) -> float | None:
        """Get the elapsed time for a completed timer.

        Args:
            label: Timer identifier.

        Returns:
            Elapsed time in milliseconds, or None if not found.
        """
        record = self._timers.get(label)
        return record.elapsed_ms if record else None

    def reset(self) -> None:
        """Clear all timer records."""
        self._timers.clear()
        self._active_starts.clear()
        logger.debug("Latency tracker reset")

    def summary(self) -> str:
        """Generate a formatted latency summary.

        Returns:
            Multi-line string with all recorded timings.
        """
        if not self._timers:
            return "No latency measurements recorded."

        lines = [
            "",
            "=" * 50,
            "  Latency Summary",
            "=" * 50,
        ]

        total = 0.0
        for label, record in self._timers.items():
            lines.append(f"  {label:<25s} {record.elapsed_ms:>8.2f} ms")
            total += record.elapsed_ms

        lines.append("  " + "-" * 40)
        lines.append(f"  {'Total':<25s} {total:>8.2f} ms")
        lines.append("=" * 50)

        report = "\n".join(lines)
        logger.info(report)
        return report
