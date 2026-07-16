"""
Benchmark utility for Gemini models.
Tests multiple Gemini Flash models to compare latency, tokens, and status.
"""

import time
import os
import sys
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# Ensure we can load env
load_dotenv()

# We can import config or just read API key directly
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def run_benchmark(prompt: str = "Explain voice activity detection in one sentence.") -> List[Dict[str, Any]]:
    """Benchmark multiple Gemini Flash models.

    Args:
        prompt: Prompt to use for testing.

    Returns:
        List of dictionaries with results for each model.
    """
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY is not set. Cannot run benchmark.", file=sys.stderr)
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Models to benchmark in order
    models_to_test = [
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash"
    ]

    results = []

    print(f"Starting benchmark with prompt: '{prompt}'\n")

    for model_name in models_to_test:
        print(f"Testing {model_name}...")
        start_time = time.perf_counter()
        
        status = "FAIL"
        latency = 0.0
        tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason = "UNKNOWN"
        response_text = ""
        error_msg = ""
        is_truncated = False

        try:
            # Configure request parameters with thinking disabled to prevent latency and truncation
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=128,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )

            # Measure request latency
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )

            latency = time.perf_counter() - start_time
            status = "PASS"

            # Parse responses defensively
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Check finish reason
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                    finish_reason = str(candidate.finish_reason)
                
                # Verify truncated response - split by dot to handle "FinishReason.STOP"
                finish_reason_clean = finish_reason.upper().split(".")[-1]
                if finish_reason_clean not in ("STOP", "NONE", "UNKNOWN", "FINISH_REASON_UNSPECIFIED"):
                    is_truncated = True

                # Extract response text
                parts = []
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            parts.append(part.text)
                response_text = "".join(parts) if parts else (response.text or "")
            else:
                response_text = response.text or ""

            # Get token usage info
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count or 0
                completion_tokens = response.usage_metadata.candidates_token_count or 0
                tokens = completion_tokens

        except APIError as exc:
            latency = time.perf_counter() - start_time
            status = "ERROR"
            error_msg = f"APIError: {exc.message}"
            logger_err = str(exc)
        except Exception as exc:
            latency = time.perf_counter() - start_time
            status = "ERROR"
            error_msg = f"Exception: {type(exc).__name__}"
            logger_err = str(exc)

        # Check if response length is suspiciously short/empty
        if status == "PASS" and not response_text.strip():
            status = "FAIL (Empty)"
        elif is_truncated:
            status = f"FAIL (Truncated: {finish_reason})"

        results.append({
            "model": model_name,
            "latency": latency,
            "tokens": tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "finish_reason": finish_reason,
            "status": status,
            "response": response_text.strip(),
            "error": error_msg
        })

    return results


def print_comparison_table(results: List[Dict[str, Any]]) -> None:
    """Print the benchmark results in a formatted comparison table."""
    if not results:
        return

    print("\n" + "=" * 80)
    print(f"{'Model':<25} | {'Latency':<10} | {'Tokens':<8} | {'Status':<15}")
    print("-" * 80)
    for res in results:
        latency_str = f"{res['latency']:.2f} s" if res['status'] != "ERROR" else "N/A"
        tokens_str = str(res['tokens']) if res['status'] == "PASS" else "N/A"
        print(f"{res['model']:<25} | {latency_str:<10} | {tokens_str:<8} | {res['status']:<15}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    results = run_benchmark()
    print_comparison_table(results)
