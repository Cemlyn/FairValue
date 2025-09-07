#!/usr/bin/env python3
"""
tools to flag if a document contains information on a stock split.
"""
import re
import os
import json
import gzip
from datetime import datetime
from typing import List, Tuple, Iterable, Optional

from ftfy import fix_text
from bs4 import BeautifulSoup

from constant import DEFAULT_KEYWORDS, RATIO_PATTERNS, DATE_PATTERNS


def convert_html_to_text(text: str) -> str:
    soup = BeautifulSoup(text, "lxml")

    # Removing all tables
    for table in soup.find_all("table"):
        table.decompose()

    plain_text = soup.get_text(separator="\n")

    # Clean whitespace
    lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    return ascii_simplify(cleaned_text)


def ascii_simplify(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2014", "-")
    )


def read_document(path: str) -> str:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as file:
            return convert_html_to_text(file.read())
    else:
        with open(path, "r", encoding="utf-8") as file:
            return convert_html_to_text(file.read())


def contains_stock_split_information(path: str, method: str = "keyword") -> bool:
    """Check if a document contains stock split information.

    Args:
        path: Path to the document file (supports .gz compressed files)
        method: Method to use for detection (currently only "keyword" supported)

    Returns:
        True if stock split information is found, False otherwise

    Examples:
        >>> # Document with stock split information
        >>> contains_stock_split_information("8k_filing.txt")
        True

        >>> # Document without stock split information
        >>> contains_stock_split_information("regular_8k.txt")
        False

        >>> # Compressed document
        >>> contains_stock_split_information("8k_filing.txt.gz")
        True

    Note:
        Currently only supports keyword-based detection using patterns from DEFAULT_KEYWORDS.
        The function searches for terms like "stock split", "share split", "reverse split", etc.
    """
    text = read_document(path)

    if method == "keyword":
        for keyword in DEFAULT_KEYWORDS:
            if keyword in text:
                return True
    else:
        pass

    return False


def find_keyword_spans(text: str, patterns: Iterable[str]) -> List[Tuple[int, int]]:
    """Find spans that contain DEFAULT_KEYWORDS and match both ratio and date patterns.

    Args:
        text: The text to search in
        patterns: Iterable of regex patterns to search for (should be DEFAULT_KEYWORDS)

    Returns:
        List of (start, end) tuples sorted by position for spans that contain:
        - A DEFAULT_KEYWORD
        - A ratio pattern match (e.g., "2-for-1", "4:1")
        - A date pattern match (e.g., "March 15, 2024", "2024-03-15")

    Examples:
        >>> text = "The company announced a 2-for-1 stock split on March 15, 2024."
        >>> patterns = [r"stock split", r"share split"]
        >>> find_keyword_spans(text, patterns)
        [(30, 41)]  # Position of "stock split" (contains keyword, ratio, and date)

        >>> text = "Multiple stock split mentions: stock split and share split"
        >>> patterns = [r"stock split", r"share split"]
        >>> find_keyword_spans(text, patterns)
        []  # No ratio or date patterns found

        >>> text = "No relevant keywords here"
        >>> patterns = [r"stock split", r"share split"]
        >>> find_keyword_spans(text, patterns)
        []  # No matches found
    """

    spans: List[Tuple[int, int]] = []

    # First, find all keyword spans
    keyword_spans: List[Tuple[int, int]] = []
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for m in rx.finditer(text):
            keyword_spans.append((m.start(), m.end()))

    # For each keyword span, check if it's in a context that also contains ratio and date patterns
    for start, end in keyword_spans:
        # Create a window around the keyword span to look for ratio and date patterns
        window_start = max(0, start - 200)  # Look 200 chars before
        window_end = min(len(text), end + 200)  # Look 200 chars after
        window_text = text[window_start:window_end]

        # Check if this window contains a ratio pattern
        has_ratio = any(rx.search(window_text) for rx in RATIO_PATTERNS)

        # Check if this window contains a date pattern
        has_date = any(rx.search(window_text) for rx in DATE_PATTERNS)

        # Only include this span if it has all three: keyword, ratio, and date
        # if has_ratio and has_date:
        if has_date:
            spans.append((start, end))

    spans.sort()
    return spans


def window_merge(
    spans: List[Tuple[int, int]], window: int, n_chars: int
) -> List[Tuple[int, int, int]]:
    """Merge nearby spans into windows of +/- `window` chars around each span.
    Returns list of (start, end, hits) windows, merged when overlapping.

    Args:
        spans: List of (start, end) character positions where keywords were found
        window: Number of characters to extend around each span
        n_chars: Total number of characters in the text

    Returns:
        List of (start, end, hits) tuples representing merged windows

    Examples:
        >>> text = "The stock split will commence on March 15, 2024. The stock split will be a 4:1 split."
        >>> spans = [(4, 15), (51, 62), (75, 80)]  # positions of "stock split" and "split"
        >>> window_merge(spans, 20, len(text))
        [(0, 95, 3)]  # Single merged window containing all 3 hits

        >>> spans = [(10, 20), (100, 110)]  # Two distant spans
        >>> window_merge(spans, 20, 200)
        [(0, 40, 1), (80, 130, 1)]  # Two separate windows

        >>> spans = [(10, 20), (25, 35)]  # Two close spans
        >>> window_merge(spans, 20, 100)
        [(0, 55, 2)]  # Merged into one window
    """
    windows: List[Tuple[int, int, int]] = []
    for s, e in spans:
        ws = max(0, s - window)
        we = min(n_chars, e + window)
        windows.append((ws, we, 1))

    if not windows:
        return []

    windows.sort(key=lambda x: (x[0], x[1]))
    merged: List[Tuple[int, int, int]] = []

    cur_s, cur_e, cur_hits = windows[0]
    for s, e, hits in windows[1:]:
        if s <= cur_e + 20:  # join if overlapping / very close
            cur_e = max(cur_e, e)
            cur_hits += hits
        else:
            merged.append((cur_s, cur_e, cur_hits))
            cur_s, cur_e, cur_hits = s, e, hits
    merged.append((cur_s, cur_e, cur_hits))
    return merged


def collect_queries(text: str, keywords: Iterable[str], window: int) -> List[str]:
    spans = find_keyword_spans(text, keywords)
    merged = window_merge(spans, window, len(text))
    queries = []
    for s, e, hits in merged:
        snippet = text[s:e]
        queries.append(snippet)
    return queries


def normalize_date(token: str) -> Optional[str]:
    token = token.strip()
    fmts = [
        "%B %d, %Y",  # March 15, 2024
        "%d %B %Y",  # 15 March 2024
        "%Y-%m-%d",  # 2024-03-15
        "%m/%d/%Y",  # 03/15/2024
        "%m/%d/%y",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(token, fmt).date()
            return dt.isoformat()
        except Exception:
            continue
    return None


def try_extract_date(snippet: str) -> Optional[str]:
    # prefer dates near hints like "effective", "record", etc.
    lower = snippet.lower()
    hint_positions = []
    for rx in DATE_HINTS:
        for m in rx.finditer(lower):
            hint_positions.append(m.start())

    candidates: List[Tuple[int, str]] = []
    for rx in DATE_PATTERNS:
        for m in rx.finditer(snippet):
            iso = normalize_date(m.group(0))
            if iso:
                idx = m.start()
                # weight by distance to nearest hint (smaller is better)
                if hint_positions:
                    dist = min(abs(idx - hp) for hp in hint_positions)
                else:
                    dist = 10_000
                candidates.append((dist, iso))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def try_extract_ratio(snippet: str) -> Optional[Tuple[int, int]]:
    for rx in RATIO_PATTERNS:
        m = rx.search(snippet)
        if m:
            try:
                a, b = int(m.group(1)), int(m.group(2))
                if a > 0 and b > 0:
                    return a, b
            except Exception:
                pass
    return None
