"""
Exceptions for the LLM Engine module.
"""

class LLMError(Exception):
    """Base exception for all LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Exception raised when an LLM request times out."""
    pass


class LLMConnectionError(LLMError):
    """Exception raised when connection to LLM API fails."""
    pass


class LLMConfigurationError(LLMError):
    """Exception raised when LLM is misconfigured (e.g. missing API key)."""
    pass
