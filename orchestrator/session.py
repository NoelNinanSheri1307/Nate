"""
Session management for Nate AI Assistant.

Tracks conversation history, current state, and registers callbacks for state changes.
"""

from typing import List, Dict, Callable, Any
from orchestrator.state import AssistantState
from orchestrator.events import PipelineEvent, StateChangedEvent
from utils.logger import setup_logger

logger = setup_logger("nate.orchestrator.session")


class ConversationSession:
    """Manages state, history, and event listeners for a conversation session."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self._state: AssistantState = AssistantState.IDLE
        self._history: List[Dict[str, str]] = []
        self._listeners: List[Callable[[PipelineEvent], None]] = []

        logger.info("Session %s created.", self.session_id)

    @property
    def state(self) -> AssistantState:
        """Get current session state."""
        return self._state

    def set_state(self, new_state: AssistantState) -> None:
        """Update session state and notify listeners.

        Args:
            new_state: The new state to transition to.
        """
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        logger.info("Session state transition: %s -> %s", old_state.value, new_state.value)

        # Notify state change
        self.emit(StateChangedEvent(old_state=old_state, new_state=new_state))

    def add_history(self, role: str, text: str) -> None:
        """Append user or assistant message to session history.

        Args:
            role: 'user' or 'assistant'.
            text: The message content.
        """
        self._history.append({"role": role, "text": text})

    def get_history(self) -> List[Dict[str, str]]:
        """Retrieve conversation history."""
        return self._history

    def clear_history(self) -> None:
        """Reset conversation history."""
        self._history.clear()
        logger.debug("Session history cleared.")

    def register_listener(self, listener: Callable[[PipelineEvent], None]) -> None:
        """Register a callback for pipeline events.

        Args:
            listener: Callback function taking a PipelineEvent.
        """
        self._listeners.append(listener)

    def unregister_listener(self, listener: Callable[[PipelineEvent], None]) -> None:
        """Remove a previously registered event listener.

        Args:
            listener: Callback function to remove.
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event: PipelineEvent) -> None:
        """Broadcast an event to all registered listeners.

        Args:
            event: The event to broadcast.
        """
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as exc:
                logger.error("Error in event listener: %s", exc)
