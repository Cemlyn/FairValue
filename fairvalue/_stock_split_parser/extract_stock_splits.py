#!/usr/bin/env python3

import os
import json
import argparse

import tqdm
import requests

from text_processing import collect_queries, read_document
from constant import DEFAULT_KEYWORDS

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL = "mistral:latest"

LLM_SYSTEM = (
    "You are a precise information extractor for SEC 8-K filings. "
    "Your task: determine if the text announces a stock split (forward or reverse). "
    "If yes, extract:\n"
    "1. The split ratio as written in the txt, e.g. '2-for-1', 'two for one', '3 to 2', etc."
    "   (e.g., '2-for-1', 'two for one', '3 to 2').\n"
    "2. The effective or record date in ISO format (YYYY-MM-DD).\n"
    "If multiple splits or dates are mentioned, choose the one explicitly tied to the split event.\n"
    "Return ONLY valid JSON with these exact keys:\n"
    "{\n"
    '  "found": true|false,\n'
    '  "type": "forward" | "reverse" | "unknown",\n'
    '  "ratio": "2-for-1" | "two for one" | null,\n'
    '  "date": "YYYY-MM-DD" | null,\n'
    '  "confidence": float between 0 and 1\n'
    "}\n"
    "If no stock split is found, set found=false, type='unknown', ratio=null, date=null.\n"
    "Do not include explanations, comments, or any text outside of the JSON."
)


def process_file(file_path: str) -> dict:

    text = read_document(file_path)

    queries = collect_queries(text=text, keywords=DEFAULT_KEYWORDS, window=120)

    results = []
    for query in queries:

        query = query.replace("\n", " ")

        prompt = build_prompt(query)

        raw = call_ollama(model=MODEL, prompt=prompt, temperature=0.0)

        data = json.loads(raw)
        data["evidence"] = query
        results.append(data)

    return results


def call_ollama(
    model: str, prompt: str, temperature: float = 0.0, timeout: int = 60
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"Failed to reach Ollama at {OLLAMA_URL}: {e}")

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama returned {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    return data.get("response", "").strip()


def build_prompt(snippet: str) -> str:
    return f"SYSTEM:\n{LLM_SYSTEM}\n\n" f"TEXT:\n{snippet}\n\n" "Return ONLY JSON."


def main():
    """Main function to process stock split documents with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract stock split information from SEC 8-K filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_stock_splits.py --filepath data/8K-filing.txt.gz --output_filepath results.json
  python extract_stock_splits.py -f data/8K-filing.txt -o output.json
        """,
    )

    parser.add_argument(
        "--filepath",
        "-f",
        required=True,
        help="Path to the input file (supports .gz compressed files)",
    )

    parser.add_argument(
        "--output_filepath",
        "-o",
        required=True,
        help="Path to the output JSON file where results will be saved",
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.filepath):
        print(f"Error: Input file '{args.filepath}' does not exist.")
        return 1

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output_filepath)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        print(f"Processing file: {args.filepath}")
        result = process_file(args.filepath)

        print(f"Saving results to: {args.output_filepath}")
        with open(args.output_filepath, "w") as f:
            json.dump(result, f, indent=4)

        print(
            f"Successfully processed {args.filepath} and saved results to {args.output_filepath}"
        )
        return 0

    except Exception as e:
        print(f"Error processing file: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
