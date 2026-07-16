"""
Unit tests for the latency mitigation background filler.
"""

import sys
import os
import time
from typing import List

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.pipeline import BackgroundFiller


class MockPiperEngine:
    def __init__(self) -> None:
        self.synthesize_called = False

    def synthesize(self, text: str) -> str:
        self.synthesize_called = True
        return "mock_filler.wav"


class MockTTSPlayer:
    def __init__(self) -> None:
        self.play_called = False
        self.stop_called = False

    def play(self, wav_path: str, blocking: bool = True) -> bool:
        self.play_called = True
        return True

    def stop(self) -> None:
        self.stop_called = True


def test_filler_trigger_exceeded() -> None:
    """Verify filler triggers and calls player if latency exceeds 800ms."""
    piper = MockPiperEngine()
    player = MockTTSPlayer()
    filler = BackgroundFiller(piper, player)

    # Start filler check thread
    filler.start()
    
    # Wait for 1.0 second (exceeds the 800ms limit)
    time.sleep(1.0)
    
    assert filler.triggered is True
    assert piper.synthesize_called is True
    assert player.play_called is True

    # Stop filler (should stop player since filler triggered)
    filler.stop()
    assert player.stop_called is True


def test_filler_trigger_cancelled() -> None:
    """Verify filler does NOT trigger if cancelled before 800ms."""
    piper = MockPiperEngine()
    player = MockTTSPlayer()
    filler = BackgroundFiller(piper, player)

    # Start filler check thread
    filler.start()
    
    # Stop before 800ms
    time.sleep(0.3)
    filler.stop()
    
    # Wait to confirm it never triggers
    time.sleep(0.6)
    
    assert filler.triggered is False
    assert piper.synthesize_called is False
    assert player.play_called is False


if __name__ == "__main__":
    print("Running filler tests...")
    test_filler_trigger_exceeded()
    test_filler_trigger_cancelled()
    print("All filler tests passed successfully!")
