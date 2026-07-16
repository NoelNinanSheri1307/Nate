"""
Conversation history manager for storing and retrieving dialogue turns.
"""

from typing import List
from memory.models import ConversationTurn


class ConversationHistory:
    """In-memory log of all conversation turns."""

    def __init__(self) -> None:
        self._turns: List[ConversationTurn] = []

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a new turn to the history."""
        self._turns.append(turn)

    def get_all(self) -> List[ConversationTurn]:
        """Get all turns in the conversation history."""
        return list(self._turns)

    def get_recent(self, limit: int) -> List[ConversationTurn]:
        """Get the most recent turns up to the specified limit.

        Args:
            limit: The maximum number of turns to return.

        Returns:
            List of the most recent ConversationTurns.
        """
        if limit <= 0:
            return []
        return self._turns[-limit:]

    def clear(self) -> None:
        """Clear all conversation history."""
        self._turns.clear()

    @property
    def size(self) -> int:
        """Get the total number of turns stored."""
        return len(self._turns)
