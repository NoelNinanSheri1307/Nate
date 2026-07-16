"""
Filler phrases for latency mitigation in real-time conversation.
"""

# Reusable list of phrases to play as filler speech when LLM generation exceeds 800ms
FILLER_PHRASES: list[str] = [
    "Let me think.",
    "Interesting question.",
    "One moment.",
    "I'm looking into that.",
    "Give me a second.",
    "Hmm, let me see."
]
