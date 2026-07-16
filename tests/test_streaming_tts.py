"""
Tests for streaming TTS sentence queue.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts.sentence_splitter import StreamingSentenceBuffer, split_sentences


def test_split_sentences_basic():
    """Verify basic sentence splitting."""
    text = "Hello there. How are you? I'm doing great!"
    sentences = split_sentences(text)
    
    assert len(sentences) == 3, f"Expected 3 sentences, got {len(sentences)}: {sentences}"
    assert sentences[0] == "Hello there."
    assert sentences[1] == "How are you?"
    assert sentences[2] == "I'm doing great!"
    print(f"✓ Basic split: {sentences}")


def test_split_empty():
    """Verify empty input returns empty list."""
    assert split_sentences("") == []
    assert split_sentences("   ") == []
    print("✓ Empty input handled correctly")


def test_streaming_buffer_progressive():
    """Verify streaming buffer yields sentences as they complete."""
    buffer = StreamingSentenceBuffer()
    
    # Simulate streaming chunks
    all_sentences = []
    
    result = buffer.feed("Hello ")
    all_sentences.extend(result)
    assert len(result) == 0, "Should not yield incomplete sentence"
    
    result = buffer.feed("there. How ")
    all_sentences.extend(result)
    assert len(result) == 1, f"Should yield one sentence, got {result}"
    assert result[0] == "Hello there."
    
    result = buffer.feed("are you? ")
    all_sentences.extend(result)
    assert len(result) == 1
    assert result[0] == "How are you?"
    
    # Flush remaining
    remaining = buffer.flush()
    all_sentences.extend(remaining)
    
    print(f"✓ Progressive buffering: {all_sentences}")


def test_streaming_buffer_flush():
    """Verify flush returns remaining buffered text."""
    buffer = StreamingSentenceBuffer()
    
    buffer.feed("Hello there")
    remaining = buffer.flush()
    assert len(remaining) == 1
    assert remaining[0] == "Hello there"
    print(f"✓ Flush returns: {remaining}")


def test_no_mid_word_split():
    """Verify sentences are not split mid-word."""
    buffer = StreamingSentenceBuffer()
    
    # Feed text that ends mid-sentence (no terminator)
    result = buffer.feed("Hello wor")
    assert len(result) == 0, f"Should not split mid-word: {result}"
    
    result = buffer.feed("ld. How are you? ")
    assert len(result) == 2
    assert result[0] == "Hello world."
    assert result[1] == "How are you?"
    
    remaining = buffer.flush()
    print(f"✓ No mid-word split. Result: {result}, remaining: {remaining}")


if __name__ == "__main__":
    print("=" * 50)
    print("  Streaming TTS Tests")
    print("=" * 50)
    
    print("\n1. Test basic sentence splitting:")
    test_split_sentences_basic()
    
    print("\n2. Test empty input:")
    test_split_empty()
    
    print("\n3. Test streaming buffer progressive:")
    test_streaming_buffer_progressive()
    
    print("\n4. Test streaming buffer flush:")
    test_streaming_buffer_flush()
    
    print("\n5. Test no mid-word split:")
    test_no_mid_word_split()
    
    print("\n" + "=" * 50)
    print("  All streaming TTS tests passed!")
    print("=" * 50)
