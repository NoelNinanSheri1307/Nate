"""
Memory Manager for coordinates conversation history and formatting for LLM inputs.
"""

from typing import List, Dict, Any
from datetime import datetime

from google.genai import types

from memory.models import ConversationTurn
from memory.history import ConversationHistory
from utils.logger import setup_logger

logger = setup_logger("nate.memory.manager")


class MemoryManager:
    """Coordinates conversation memory and formatting for Gemini Client."""

    def __init__(self, default_limit: int = 8) -> None:
        self._history = ConversationHistory()
        self.default_limit = default_limit

    def add_user_turn(self, text: str) -> None:
        """Record a user message turn."""
        turn = ConversationTurn(role="user", text=text)
        self._history.add_turn(turn)
        logger.info("Recorded User turn (Total memory size: %d)", self._history.size)

    def add_assistant_turn(self, text: str) -> None:
        """Record an assistant message turn."""
        turn = ConversationTurn(role="assistant", text=text)
        self._history.add_turn(turn)
        logger.info("Recorded Assistant turn (Total memory size: %d)", self._history.size)

    def get_history_for_gemini(self, limit: int | None = None) -> List[types.Content]:
        """Format the recent history as a list of google-genai Content structures.

        Args:
            limit: Configurable number of recent turns. Defaults to self.default_limit.

        Returns:
            List of types.Content objects.
        """
        lim = limit if limit is not None else self.default_limit
        recent_turns = self._history.get_recent(lim)
        
        contents = []
        for turn in recent_turns:
            # Map roles: user -> user, assistant -> model (Gemini SDK standard)
            role = "user" if turn.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn.text)]
                )
            )
        return contents

    def get_all_turns(self) -> List[ConversationTurn]:
        """Retrieve all turns stored in history."""
        return self._history.get_all()

    def clear(self) -> None:
        """Clear all stored conversation turns."""
        self._history.clear()

    @property
    def total_turns(self) -> int:
        """Get total number of turns stored."""
        return self._history.size
