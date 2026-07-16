"""
Test suite and benchmark runner for Gemini models in Nate.

Benchmarks every supported Gemini model, prints results,
and recommends the fastest working model.
"""

import sys
import os

# Ensure project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.model_benchmark import run_benchmark, print_comparison_table
from utils.logger import setup_logger

logger = setup_logger("nate.test.llm_benchmark", level="INFO")


def main() -> None:
    """Run the model benchmark and make recommendations."""
    print("\n" + "=" * 60)
    print("  NATE — LLM Subsystem Benchmark & Selection Test")
    print("=" * 60)

    # Run benchmark with a standard conversational prompt
    results = run_benchmark(prompt="Tell me a one-sentence joke about computers.")

    if not results:
        print("\n[ERROR] No results returned. Please verify GEMINI_API_KEY is configured.")
        sys.exit(1)

    # Print comparison table
    print_comparison_table(results)

    # Print detailed info for each tested model
    print("\n--- Detailed Model Output ---")
    fastest_model = None
    min_latency = float("inf")

    for res in results:
        print(f"\nModel: {res['model']}")
        print(f"  Status:        {res['status']}")
        if res['status'] == "ERROR":
            print(f"  Error:         {res['error']}")
        else:
            print(f"  Latency:       {res['latency']:.2f} seconds")
            print(f"  Tokens:        Prompt: {res['prompt_tokens']} | Completion: {res['completion_tokens']}")
            print(f"  Finish Reason: {res['finish_reason']}")
            print(f"  Response:      \"{res['response']}\"")

            # Evaluate for fastest working model recommendation
            # Only recommend models that passed successfully (status == "PASS")
            if res['status'] == "PASS" and res['latency'] < min_latency:
                min_latency = res['latency']
                fastest_model = res['model']

    print("\n" + "=" * 60)
    print("  RECOMMENDATION")
    print("=" * 60)
    if fastest_model:
        print(f"  Fastest working model: {fastest_model}")
        print(f"  Measured latency:      {min_latency:.2f} seconds")
        print("\n  To use this model, set it in your .env file:")
        print(f"  GEMINI_MODEL={fastest_model}")
    else:
        print("  No models successfully passed the benchmark.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
