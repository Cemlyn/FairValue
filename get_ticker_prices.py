import requests
import sys
import time
import tqdm
import json
import os

import pandas as pd

# Replace with your Polygon.io API key
API_KEY = os.getenv("POLYGON_API_KEY", default=None)
API_KEY = "HicWT_23n7WSfrv0ywH9_7lfefuix1me"

# Base URL for Polygon.io
BASE_URL = "https://api.polygon.io/v2/aggs/ticker"
LATEST_DATE = "latest_10k"


def get_current_price(ticker):
    """Fetch the current price of a stock ticker from Polygon.io."""
    url = f"{BASE_URL}/{ticker}/prev?adjusted=true&apiKey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", None)
        results = results[0] if results else None
        return results
    except requests.RequestException as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None


def main(csv_file):
    """Read tickers from a CSV file and fetch their prices."""
    df = pd.read_csv(csv_file, parse_dates=[LATEST_DATE])
    df[LATEST_DATE] = df[LATEST_DATE].dt.date

    tickers = df["ticker_id"].values.tolist()
    latest_dates = df[LATEST_DATE].values.tolist()
    data = zip(tickers, latest_dates)
    counter = 0
    for ticker, latest_date in tqdm.tqdm(data):
        counter += 1
        if pd.isnull(ticker) or pd.isnull(latest_date):
            price = {
                "T": ticker,
                "v": None,
                "vw": None,
                "o": None,
                "c": None,
                "h": None,
                "l": None,
                "t": None,
                "n": None,
            }
        elif latest_date <= pd.Timestamp("2023-12-01").date():
            price = {
                "T": ticker,
                "v": None,
                "vw": None,
                "o": None,
                "c": None,
                "h": None,
                "l": None,
                "t": None,
                "n": None,
            }
        else:
            price = get_current_price(ticker)

            if price is None:
                price = {
                    "T": None,
                    "v": None,
                    "vw": None,
                    "o": None,
                    "c": None,
                    "h": None,
                    "l": None,
                    "t": None,
                    "n": None,
                }

            time.sleep(0.05)

        json_line = json.dumps(price)

        with open("outputs.jsonl", "a") as file:
            file.write(json_line + "\n")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python script.py <csv_file>")
    else:
        csv_file = sys.argv[1]
        main(csv_file)
