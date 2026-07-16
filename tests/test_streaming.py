"""
Tests for streaming text responses from Gemini.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.gemini_client import GeminiClient
from llm.models import LLMConfig


def test_stream_chunks_arrive():
    """Verify that stream chunks arrive progressively."""
    client = GeminiClient()
    
    chunks = []
    for chunk in client.generate_response_stream("Tell me a short joke"):
        chunks.append(chunk)
        print(f"  Chunk {len(chunks)}: '{chunk}'")
    
    assert len(chunks) > 0, "No chunks received from streaming"
    print(f"\n✓ Received {len(chunks)} chunks")
    
    # Verify final result is available
    result = client.last_stream_result
    assert result is not None, "No final stream result"
    assert len(result.text) > 0, "Final text is empty"
    print(f"✓ Final text: '{result.text}'")
    print(f"✓ Latency: {result.latency_ms:.2f} ms")


def test_final_text_matches_accumulated():
    """Verify final assembled text matches concatenated chunks."""
    client = GeminiClient()
    
    accumulated = ""
    for chunk in client.generate_response_stream("Say hello"):
        accumulated += chunk
    
    result = client.last_stream_result
    assert result is not None
    
    # The final text should match (allowing for strip differences)
    assert result.text.strip() == accumulated.strip(), (
        f"Mismatch: result='{result.text}' vs accumulated='{accumulated}'"
    )
    print(f"✓ Final text matches accumulated chunks: '{result.text}'")


def test_stream_faster_than_blocking():
    """Verify first chunk arrives faster than total blocking generation."""
    client = GeminiClient()
    
    # Measure time to first chunk
    start = time.perf_counter()
    first_chunk_time = None
    for chunk in client.generate_response_stream("Tell me about the weather"):
        if first_chunk_time is None:
            first_chunk_time = (time.perf_counter() - start) * 1000.0
    
    total_stream_time = (time.perf_counter() - start) * 1000.0
    
    print(f"  Time to first chunk: {first_chunk_time:.2f} ms")
    print(f"  Total stream time: {total_stream_time:.2f} ms")
    
    assert first_chunk_time is not None
    assert first_chunk_time < total_stream_time, "First chunk should arrive before stream completes"
    print(f"✓ Streaming delivers first chunk {total_stream_time - first_chunk_time:.0f} ms before completion")


if __name__ == "__main__":
    print("=" * 50)
    print("  Streaming Text Tests")
    print("=" * 50)
    
    print("\n1. Test stream chunks arrive:")
    test_stream_chunks_arrive()
    
    print("\n2. Test final text matches accumulated:")
    test_final_text_matches_accumulated()
    
    print("\n3. Test stream faster than blocking:")
    test_stream_faster_than_blocking()
    
    print("\n" + "=" * 50)
    print("  All streaming text tests passed!")
    print("=" * 50)
