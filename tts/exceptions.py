"""
Custom exception classes for the TTS subsystem.
"""

class TTSError(Exception):
    """Base class for all TTS exceptions."""
    pass


class TTSInitializationError(TTSError):
    """Exception raised when Piper engine fails to initialize."""
    pass


class TTSSynthesisError(TTSError):
    """Exception raised when speech synthesis fails."""
    pass
