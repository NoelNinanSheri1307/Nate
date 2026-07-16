"""
Assistant states for the Orchestrator.
"""

from enum import Enum


class AssistantState(Enum):
    """Enumeration of possible assistant states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
