"""
Unit tests for the conversation memory subsystem.
"""

import sys
import os
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.models import ConversationTurn
from memory.history import ConversationHistory
from memory.manager import MemoryManager


def test_conversation_turn() -> None:
    """Test that ConversationTurn stores attributes correctly."""
    turn = ConversationTurn(role="user", text="hello")
    assert turn.role == "user"
    assert turn.text == "hello"
    assert isinstance(turn.timestamp, datetime)


def test_conversation_history() -> None:
    """Test ConversationHistory storage and retrieval."""
    history = ConversationHistory()
    assert history.size == 0

    turn1 = ConversationTurn(role="user", text="hello")
    turn2 = ConversationTurn(role="assistant", text="hi there")
    
    history.add_turn(turn1)
    history.add_turn(turn2)
    
    assert history.size == 2
    turns = history.get_all()
    assert len(turns) == 2
    assert turns[0].text == "hello"
    assert turns[1].text == "hi there"

    # Test limit retrieval
    recent = history.get_recent(1)
    assert len(recent) == 1
    assert recent[0].text == "hi there"


def test_memory_manager() -> None:
    """Test MemoryManager role conversion and turn limit truncation."""
    manager = MemoryManager(default_limit=2)

    manager.add_user_turn("first message")
    manager.add_assistant_turn("first reply")
    manager.add_user_turn("second message")

    assert manager.total_turns == 3

    # get_history_for_gemini should only return the last 2 turns due to default_limit=2
    contents = manager.get_history_for_gemini()
    assert len(contents) == 2
    
    # First contents in the returned limit should map to "first reply" (assistant -> model)
    assert contents[0].role == "model"
    assert contents[0].parts[0].text == "first reply"

    assert contents[1].role == "user"
    assert contents[1].parts[0].text == "second message"

    # Verify custom limit overrides
    all_contents = manager.get_history_for_gemini(limit=3)
    assert len(all_contents) == 3


if __name__ == "__main__":
    print("Running memory tests...")
    test_conversation_turn()
    test_conversation_history()
    test_memory_manager()
    print("All memory tests passed successfully!")
