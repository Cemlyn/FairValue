import os
import json
import pytest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_processing import (
    read_document,
    contains_stock_split_information,
    find_keyword_spans,
    window_merge,
)

from constant import DEFAULT_KEYWORDS


def test_contains_stock_split_information():

    filepath = os.path.join(os.path.dirname(__file__), "..", "data")

    with open(os.path.join(filepath, "training_data.json"), "r") as file:
        data = json.load(file)

    for file, is_split in data.items():
        assert (
            contains_stock_split_information(os.path.join(filepath, file)) == is_split
        )


def test_find_keyword_spans():

    # Text with keyword, ratio, and date - should match
    positive_text = "On March 15, 2024, the company announced a 2-for-1 stock split."

    # Text with keyword and date but no ratio - should not match
    text_no_ratio = "On March 15, 2024, the company announced a stock split."

    # Text with keyword and ratio but no date - should not match
    text_no_date = "The company announced a 2-for-1 stock split."

    # Text with keyword but no ratio or date - should not match
    negative_text = (
        "This is a test of the find_keyword_spans function with stock split."
    )

    positive_spans = find_keyword_spans(positive_text, DEFAULT_KEYWORDS)
    no_ratio_spans = find_keyword_spans(text_no_ratio, DEFAULT_KEYWORDS)
    no_date_spans = find_keyword_spans(text_no_date, DEFAULT_KEYWORDS)
    negative_spans = find_keyword_spans(negative_text, DEFAULT_KEYWORDS)

    assert isinstance(positive_spans, list)
    assert isinstance(negative_spans, list)
    assert len(positive_spans) == 1  # Should find the stock split with ratio and date
    assert len(no_ratio_spans) == 0  # No ratio pattern, should not match
    assert len(no_date_spans) == 0  # No date pattern, should not match
    assert len(negative_spans) == 0  # No ratio or date patterns, should not match
    assert positive_spans[0] == (51, 62)  # Position of "stock split"


def test_window_merge():

    # Text with multiple stock split mentions, each with ratio and date patterns
    text = """The company announced a 2-for-1 stock split on March 15, 2024. 
    The stock split will be a 4:1 split effective April 1, 2024."""

    text_spans = find_keyword_spans(text, DEFAULT_KEYWORDS)

    # Should find both stock split mentions since they both have ratio and date patterns
    assert len(text_spans) == 2

    merged = window_merge(text_spans, 100, len(text))
    # Should merge into one window since they're close together
    assert len(merged) == 1
    assert merged[0][2] == 2  # Should have 2 hits
