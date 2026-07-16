"""
Sentence splitter for streaming TTS.

Buffers incoming text chunks and yields complete sentences
suitable for independent TTS synthesis.
"""

import re
from typing import Generator


# Sentence-ending punctuation patterns
_SENTENCE_ENDINGS = re.compile(r'(?<=[.!?])\s+')
_SENTENCE_TERMINATORS = {'.', '!', '?'}


def split_sentences(text: str) -> list[str]:
    """Split text into sentences for TTS synthesis.

    Args:
        text: Full text to split.

    Returns:
        List of sentence strings.
    """
    if not text or not text.strip():
        return []
    
    # Split on sentence-ending punctuation followed by whitespace
    parts = _SENTENCE_ENDINGS.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


class StreamingSentenceBuffer:
    """Buffers streaming text chunks and yields complete sentences.
    
    Accumulates text from stream chunks and emits sentences as soon as
    a sentence-ending punctuation mark is detected. Ensures no mid-word splits.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[str]:
        """Feed a text chunk and return any complete sentences.

        Args:
            chunk: Text chunk from the streaming API.

        Returns:
            List of complete sentences ready for TTS. May be empty.
        """
        self._buffer += chunk
        sentences = []
        
        # Scan for sentence boundaries
        while True:
            # Find the earliest sentence terminator
            best_pos = -1
            for term in _SENTENCE_TERMINATORS:
                pos = self._buffer.find(term)
                if pos != -1:
                    # Make sure it's followed by whitespace or end of buffer context
                    # to avoid splitting on abbreviations like "Dr." mid-word
                    after = pos + 1
                    if after < len(self._buffer):
                        if self._buffer[after] in (' ', '\n', '\t', '\r'):
                            if best_pos == -1 or pos < best_pos:
                                best_pos = after
                    # At the very end of buffer, don't emit yet — wait for more text
                    # unless buffer is being flushed
            
            if best_pos == -1:
                break
            
            sentence = self._buffer[:best_pos].strip()
            self._buffer = self._buffer[best_pos:].lstrip()
            
            if sentence:
                sentences.append(sentence)
        
        return sentences

    def flush(self) -> list[str]:
        """Flush any remaining buffered text as a final sentence.

        Returns:
            List containing the remaining text, or empty if buffer is clean.
        """
        remaining = self._buffer.strip()
        self._buffer = ""
        if remaining:
            return [remaining]
        return []

    @property
    def pending(self) -> str:
        """Get currently buffered but unemitted text."""
        return self._buffer
