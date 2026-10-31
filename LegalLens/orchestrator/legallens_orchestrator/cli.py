"""Command-line entry point for trying the standalone classifier."""

from __future__ import annotations

import argparse

from .classifier import classify_intent


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify a LegalLens message.")
    parser.add_argument("message", nargs="?", help="Message to classify; omit for interactive input.")
    args = parser.parse_args()
    message = args.message if args.message is not None else input("Message: ")
    result = classify_intent(message)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
