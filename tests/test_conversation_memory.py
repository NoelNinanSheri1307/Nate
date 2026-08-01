"""
Multi-turn integration test for validating conversation memory with Gemini.

Sends the user's exact conversation sequence and prints the memory debug blocks
to verify contextual understanding and turn-alternation consistency.
"""

import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from llm.gemini_client import GeminiClient
from memory.manager import MemoryManager


def main() -> None:
    print("=" * 60)
    print("  NATE — Conversation Memory Subsystem Validation")
    print("=" * 60)

    if not config.validate_config():
        print("[ERROR] Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
        sys.exit(1)

    # Initialize components
    client = GeminiClient()
    memory = MemoryManager(default_limit=8)

    # The exact verification script sequence requested by the user
    conversation_steps = [
        "Hello.",
        "My name is Noel.",
        "Remember that.",
        "What is my name?",
        "What did I ask first?",
        "Summarize our conversation.",
        "Who are you?",
        "What did I tell you earlier?"
    ]

    for i, user_message in enumerate(conversation_steps, 1):
        print(f"\n--- Turn {i}: User says: '{user_message}' ---")
        
        # 1. Record User Turn
        memory.add_user_turn(user_message)
        
        # 2. Construct Prompt (Retrieves list of types.Content)
        history_contents = memory.get_history_for_gemini()
        
        # 3. Call LLM (Which prints the detailed diagnostics log block internally)
        try:
            response = client.generate_response(history_contents)
            
            # 4. Record Assistant Turn
            memory.add_assistant_turn(response.text)
            
            print(f"Assistant Response:\n{response.text}")
            print(f"Stored Turns in Memory: {memory.total_turns}")
            
        except Exception as exc:
            print(f"[ERROR] LLM Generation failed: {exc}")
            # Rollback to preserve turn alternation consistency
            memory.rollback_last_user_turn()
            break

    print("\n" + "=" * 60)
    print("  Conversation Memory Validation Script Complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
