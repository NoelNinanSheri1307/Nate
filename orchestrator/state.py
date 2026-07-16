"""
Assistant states for the Orchestrator.
"""

from enum import Enum


class AssistantState(Enum):
    """Enumeration of possible assistant states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    STREAMING = "streaming"
    SPEAKING = "speaking"
    WAKE_LISTENING = "wake_listening"
    ERROR = "error"
