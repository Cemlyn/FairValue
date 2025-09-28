#!/usr/bin/env python3

import os
import json
import argparse
import re
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import tqdm
import requests

from fairvalue._stock_split_parser.text_processing import collect_queries, read_document
from fairvalue._stock_split_parser.constant import DEFAULT_KEYWORDS

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
    """Process a single file and extract stock split information."""
    text = read_document(file_path)

    queries = collect_queries(text=text, keywords=DEFAULT_KEYWORDS, window=120)

    results = []
    for query in queries:

        query = query.replace("\n", " ")

        prompt = build_prompt(query)

        raw = call_ollama(model=MODEL, prompt=prompt, temperature=0.0)

        data = json.loads(raw)
        data["evidence"] = query
        data["filename"] = file_path

        # Add normalized fields
        data["normalized_ratio"] = normalize_ratio(data.get("ratio"))
        data["normalized_date"] = normalize_date(data.get("date"))

        results.append(data)

    results = {
        "filename": file_path,
        "model": MODEL,
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }

    return results


def process_directory(directory_path: str, regex_pattern: str) -> list:
    """Process all files in a directory that match the regex pattern."""
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory '{directory_path}' does not exist.")

    if not directory.is_dir():
        raise NotADirectoryError(f"'{directory_path}' is not a directory.")

    # Compile the regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{regex_pattern}': {e}")

    # Find all files in the directory (including subdirectories)
    all_files = []
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            all_files.append(file_path)

    # Filter files that match the regex pattern
    matching_files = []
    for file_path in all_files:
        if pattern.search(str(file_path)):
            matching_files.append(str(file_path))

    if not matching_files:
        print(
            f"Warning: No files found matching pattern '{regex_pattern}' in directory '{directory_path}'"
        )
        return []

    print(f"Found {len(matching_files)} files matching pattern '{regex_pattern}'")

    # Process each matching file
    all_results = []
    for file_path in tqdm.tqdm(matching_files, desc="Processing files"):
        try:
            result = process_file(file_path)
            all_results.append(result)
        except Exception as e:
            print(f"Error processing file '{file_path}': {e}")
            # Continue processing other files even if one fails
            continue

    return all_results


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


def normalize_ratio(ratio: Optional[str]) -> Optional[str]:
    """
    Normalize stock split ratio to a consistent format.

    Args:
        ratio: The ratio string as extracted from the document (e.g., "3-for-2", "3 to 2", "4-for-1")

    Returns:
        Normalized ratio in format "X:Y" or None if ratio is null/invalid

    Raises:
        ValueError: If the ratio string doesn't match any expected pattern
    """
    if not ratio or ratio.lower() in ["not specified", "null", "none"]:
        return None

    # Remove extra whitespace and convert to lowercase
    ratio = ratio.strip().lower()

    # Handle different ratio formats
    # Pattern 1: "X-for-Y" or "X for Y" (supports decimals, allows extra text after)
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*[-]?\s*(?:for|to)\s*[-]?\s*(\d+(?:\.\d+)?)", ratio
    )
    if match:
        x, y = match.groups()
        return f"{x}:{y}"

    # Pattern 2: Already in "X:Y" format (supports decimals)
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", ratio)
    if match:
        x, y = match.groups()
        return f"{x}:{y}"

    # If no pattern matches, raise an error
    raise ValueError(
        f"Unable to normalize ratio string: '{ratio}'. Expected formats: 'X-for-Y', 'X to Y', 'X:Y', or null/not specified"
    )


def normalize_date(date: Optional[str]) -> Optional[str]:
    """
    Normalize date to ISO format (YYYY-MM-DD).

    Args:
        date: The date string as extracted from the document

    Returns:
        Normalized date in ISO format (YYYY-MM-DD) or None if date is null/invalid
    """
    if not date or date.lower() in ["null", "none", "not specified"]:
        return None

    # Try to parse various date formats
    date_formats = [
        "%Y-%m-%d",  # ISO format
        "%m/%d/%Y",  # MM/DD/YYYY
        "%m-%d-%Y",  # MM-DD-YYYY
        "%Y/%m/%d",  # YYYY/MM/DD
        "%B %d, %Y",  # Month DD, YYYY
        "%b %d, %Y",  # Mon DD, YYYY
        "%d %B %Y",  # DD Month YYYY
        "%d %b %Y",  # DD Mon YYYY
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date.strip(), fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If no format matches, raise an error
    raise ValueError(
        f"Unable to normalize date string: '{date}'. Expected formats: ISO (YYYY-MM-DD), MM/DD/YYYY, Month DD YYYY, etc."
    )


def main():
    """Main function to process stock split documents with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract stock split information from SEC 8-K filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file:
  python extract_stock_splits.py --filepath data/8K-2021-05-26-0001045810-21-000063.txt.gz --output_filepath results.json
  python extract_stock_splits.py -f data/8K-2021-05-26-0001045810-21-000063.txt.gz -o output.json
  
  # Process all 8-K files in a directory:
  python extract_stock_splits.py --dir data/ --regex "8K-.*\\.txt\\.gz$" --output_filepath results.json
  python extract_stock_splits.py -d data/ -r "8K-.*\\.txt\\.gz$" -o output.json
  
  # Process files from a specific year:
  python extract_stock_splits.py --dir data/ --regex "8K-2021-.*\\.txt\\.gz$" --output_filepath results_2021.json
        """,
    )

    # Create mutually exclusive group for file vs directory processing
    input_group = parser.add_mutually_exclusive_group(required=True)

    input_group.add_argument(
        "--filepath",
        "-f",
        help="Path to the input file (supports .gz compressed files)",
    )

    input_group.add_argument(
        "--dir",
        "-d",
        help="Path to the directory containing files to process",
    )

    parser.add_argument(
        "--regex",
        "-r",
        help="Regex pattern to match files when using --dir (required when --dir is specified)",
    )

    parser.add_argument(
        "--output_filepath",
        "-o",
        required=True,
        help="Path to the output JSON file where results will be saved",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.dir and not args.regex:
        print("Error: --regex is required when using --dir")
        return 1

    if args.filepath and not os.path.exists(args.filepath):
        print(f"Error: Input file '{args.filepath}' does not exist.")
        return 1

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output_filepath)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        if args.filepath:
            # Process single file
            print(f"Processing file: {args.filepath}")
            result = process_file(args.filepath)

            print(f"Saving results to: {args.output_filepath}")
            with open(args.output_filepath, "w") as f:
                json.dump(result, f, indent=4)

            print(
                f"Successfully processed {args.filepath} and saved results to {args.output_filepath}"
            )

        else:
            # Process directory
            print(f"Processing directory: {args.dir} with pattern: {args.regex}")
            results = process_directory(args.dir, args.regex)

            if not results:
                print("No files were processed.")
                return 0

            # Save all results
            output_data = {
                "directory": args.dir,
                "regex_pattern": args.regex,
                "model": MODEL,
                "timestamp": datetime.now().isoformat(),
                "total_files_processed": len(results),
                "results": results,
            }

            print(f"Saving results to: {args.output_filepath}")
            with open(args.output_filepath, "w") as f:
                json.dump(output_data, f, indent=4)

            print(
                f"Successfully processed {len(results)} files and saved results to {args.output_filepath}"
            )

        return 0

    except Exception as e:
        print(f"Error processing: {e}")
        return 1
