"""
Structured AssistantResponse dataclass for LLM outputs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantResponse:
    """Structured response from the LLM engine.

    Attributes:
        text: The generated response text.
        prompt_tokens: Number of tokens in the input prompt (if available).
        response_tokens: Number of tokens in the generated response (if available).
        latency_ms: Latency of the LLM generation in milliseconds.
    """
    text: str
    prompt_tokens: int
    response_tokens: int
    latency_ms: float

    def __str__(self) -> str:
        return (
            f"AssistantResponse(latency={self.latency_ms:.2f}ms, "
            f"prompt_tokens={self.prompt_tokens}, response_tokens={self.response_tokens})\n"
            f"  \"{self.text}\""
        )
