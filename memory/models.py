"""
Data models for the memory subsystem.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ConversationTurn:
    """Represents a single turn (message) in the conversation history.

    Attributes:
        role: The role of the speaker ('user' or 'assistant').
        text: The text content of the message.
        timestamp: The datetime when this turn occurred.
    """
    role: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
