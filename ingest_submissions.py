"""
SEC Ticker Mapping Script

This script processes SEC bulk submission data to create a mapping between CIK (Central Index Key) numbers 
and the corresponding ticker symbols for publicly listed companies. The script handles the following:

1. Loads submission data files from a specified directory ('data/submissions').
2. Extracts the most relevant ticker and exchange information for each CIK:
   - If the company has multiple tickers (e.g., common stock and debt securities), 
     it attempts to identify the common stock ticker (typically the shortest ticker).
   - Focuses on exchanges like NYSE and NASDAQ where applicable.
3. Saves the resulting CIK-to-ticker mapping as a serialized file ('ticker_mapping.pkl') for future use.

### Key Notes:
- The output is a Python dictionary saved in the file 'data/ticker_mapping.pkl'.
- If the mapping file already exists, it will be loaded instead of being regenerated.

Ensure the `data/submissions` directory exists, where the submissions folder is the extracted
content of the bulk submissions file which can be found 
on the SEC website: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip 
"""

import os
import json
import pickle
import logging
from logging import StreamHandler, FileHandler
from logging.config import dictConfig
from typing import Dict

import numpy as np

from fairvalue.utils import load_json
from fairvalue.models.ingestion import ParseException
from logger_conf import get_logger

DIR = "data"

logger = get_logger("SEC_Ticker_Mapping")


def search_ticker(submission: dict = None) -> Dict[str, str]:

    if submission is None:
        raise ValueError("submission dict is None.")

    empty_response = {"ticker": None, "exchange": None}

    if len(submission["tickers"]) != len(submission["exchanges"]):
        raise ParseException(
            "cannot create mapping. 'tickers' and 'exchanges' values are different in length."
        )

    if ("tickers" not in submission) or ("exchanges" not in submission):
        return empty_response

    if (len(submission["tickers"]) == 0) or (len(submission["exchanges"]) == 0):
        return empty_response

    for ticker, exchange in zip(submission["tickers"], submission["exchanges"]):
        if (exchange is not None) and (exchange.lower() in ["nyse", "nasdaq"]):
            return {"ticker": ticker, "exchange": exchange}

    """
    This section attempts to find the ticker that
    represents the common stock for companies which
    have multiple ticker associated with the company cik.
    For example, Ford Motor company has the ticker 'F' for 
    its common stock, and 'F-PC' for its debt securities.

    Typically the common stock ticker is the shortest.
    """
    shortest_ticker = None
    shortest_ticker_len = np.inf
    shortest_ticker_exchange = None
    for i in range(len(submission["tickers"])):

        if shortest_ticker is None:
            shortest_ticker = submission["tickers"][i]
            shortest_ticker_len = len(shortest_ticker)
            shortest_ticker_exchange = submission["exchanges"][i]

        elif len(submission["tickers"][i]) < shortest_ticker_len:
            shortest_ticker = submission["tickers"][i]
            shortest_ticker_len = len(shortest_ticker)
            shortest_ticker_exchange = submission["exchanges"][i]

    return {"ticker": shortest_ticker, "exchange": shortest_ticker_exchange}


if __name__ == "__main__":

    SUBMISSIONS_DIR = os.path.join(DIR, "submissions")
    OUTPUT_FILEPATH = os.path.join(DIR, "ticker_mapping.pkl")

    files = os.listdir(SUBMISSIONS_DIR)

    ticker_dict = dict()
    for file in files:
        try:
            submission = load_json(os.path.join(DIR, "submissions", file))

        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSON file: %s", file)
            continue

        if ("cik" not in submission) or (submission["cik"] is None):
            logger.warning("Skipping file with missing or None CIK: %s", file)
            continue

        cik = str(submission["cik"]).lstrip("0")
        ticker_dict[cik] = search_ticker(submission)

    logger.info(
        "Processed %d submissions out of %d. Saving ticker mapping.",
        len(ticker_dict),
        len(files),
    )
    with open(OUTPUT_FILEPATH, "wb") as file:
        pickle.dump(ticker_dict, file)
