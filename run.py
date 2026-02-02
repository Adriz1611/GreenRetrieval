#!/usr/bin/env python3
"""Command-line interface for GreenRetrieval."""

import sys
from pathlib import Path

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from src import diagnose
from src.config import Config
from src.eppo_client import EPPOClient
from src.generation import ResponseGenerator


def main():
    """Run plant disease diagnosis from command line."""
    # Validate configuration
    try:
        Config.validate()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease ensure:")
        print("  1. EPPO_SQLITE_PATH points to valid database")
        print("  2. EPPO_API_KEY environment variable is set")
        print("  3. GROQ_API_KEY environment variable is set")
        sys.exit(1)

    # Example disease labels
    labels = [
        "Rice leaf blast",
        "Wheat leaf rust",
        "Potato leaf late blight",
    ]

    # Initialize shared clients
    eppo_client = EPPOClient()
    generator = ResponseGenerator()

    print("🌿 GreenRetrieval - Plant Disease Diagnosis")
    print("=" * 80)
    print(f"Database: {Config.SQLITE_PATH}")
    print(f"Confidence Threshold: {Config.CONFIDENCE_THRESHOLD}")
    print(f"Model: {Config.GROQ_MODEL}")
    print("=" * 80)

    # Process labels
    results = []
    iterator = tqdm(labels, desc="🔬 Diagnosing") if HAS_TQDM else labels

    for label in iterator:
        if not HAS_TQDM:
            print(f"\n🔬 Diagnosing: {label}")

        result = diagnose(
            label,
            eppo_client=eppo_client,
            generator=generator,
        )
        results.append((label, result))

        # Display result
        status = "🚫 REFUSED" if result.refused else "✅ VERIFIED"
        print(f"\n{status}: {label}")
        print("-" * 80)
        print(result.message)

        if result.eppocode:
            print(f"\n📋 EPPO Code: {result.eppocode}")
        if result.confidence is not None:
            print(f"🎯 Confidence: {result.confidence:.2%}")

    # Display summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY STATISTICS")
    print("=" * 80)

    verified = sum(1 for _, r in results if not r.refused)
    refused = len(results) - verified
    avg_conf = (
        sum(r.confidence or 0 for _, r in results if r.confidence) / len(results)
    )

    print(f"✅ Verified: {verified}/{len(results)} ({verified/len(results)*100:.1f}%)")
    print(f"🚫 Refused: {refused}/{len(results)} ({refused/len(results)*100:.1f}%)")
    print(f"🎯 Average Confidence: {avg_conf:.2%}")

    # Client stats
    eppo_stats = eppo_client.get_stats()
    gen_stats = generator.get_stats()

    print(f"\n💾 EPPO API Cache:")
    print(f"   Hits: {eppo_stats['cache_hits']} (reused from disk)")
    print(f"   Misses: {eppo_stats['cache_misses']} (fetched from API)")
    print(f"   Total API Calls: {eppo_stats['api_calls']}")
    print(f"\n🤖 Groq LLM Calls: {gen_stats['call_count']}")
    print("=" * 80)


if __name__ == "__main__":
    main()