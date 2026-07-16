"""
Model definitions and parameters for the LLM subsystem.
"""

from dataclasses import dataclass
import config


@dataclass(frozen=True)
class LLMConfig:
    """Configuration parameters for the Gemini client."""
    model_name: str = config.LLM_MODEL
    temperature: float = 0.2
    top_p: float = 0.9
    max_output_tokens: int = 128
    timeout_seconds: float = 10.0
    max_retries: int = 3

