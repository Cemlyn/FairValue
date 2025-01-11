import os
import json
import pickle

import tqdm
import pandas as pd

from utils import load_json, datum_to_dataframe
from models.ingestion import CompanyFacts

from pydantic import ValidationError
from json import JSONDecodeError


def check_filepath(filepath: str) -> str:

    if os.path.isfile(filepath):
        return check_filepath(f"{filepath}.out")
    return filepath


def process_company_facts(filepath: str, ticker_mapping: dict) -> list:
    """
    Processes company facts from a JSON file and generates a list of records
    containing yearly financial data.

    Args:
        filepath (str): Path to the JSON file containing company facts.
        ticker_mapping (dict): A dictionary mapping CIK (Central Index Key) to ticker symbols.

    Returns:
        list: A list of dictionaries containing processed financial data with keys:
              - 'end': End date of the financial period.
              - 'filed': Filing date of the report.
              - 'form': Form type (e.g., '10-K').
              - 'net_cashflow_ops': Net cash flow from operating activities.
              - 'capital_expenditure': Capital expenditures.
              - 'shares_outstanding': Number of shares outstanding.
              - 'cik': Central Index Key.
              - 'entityName': Entity name.
              - 'ticker': Ticker symbol (if available).
    """
    json_data = load_json(filepath)
    company_facts = CompanyFacts(**json_data)

    if company_facts.facts.dei.EntityCommonStockSharesOutstanding:
        shares = company_facts.facts.dei.EntityCommonStockSharesOutstanding.units.shares
        shares_df = datum_to_dataframe(shares, "shares_outstanding")
        shares_df = shares_df[~shares_df["frame"].isna()]
    else:
        shares = pd.DataFrame(columns=["end", "filed", "form", "shares_outstanding"])

    if company_facts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities:
        netcashflow = (
            company_facts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units.USD
        )
        netcashflow_df = datum_to_dataframe(netcashflow, "net_cashflow_ops")
        netcashflow_df = netcashflow_df[~netcashflow_df["frame"].isna()]
    else:
        netcashflow_df = pd.DataFrame(
            columns=["end", "filed", "form", "net_cashflow_ops"]
        )

    if company_facts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment:
        capex = (
            company_facts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units.USD
        )
        capex_df = datum_to_dataframe(capex, "capital_expenditure")
        capex_df = capex_df[~capex_df["frame"].isna()]
    else:
        capex_df = pd.DataFrame(columns=["end", "filed", "form", "capital_expenditure"])

    # Combine cashflow and capex
    merged = netcashflow_df[["end", "filed", "form", "net_cashflow_ops"]].merge(
        capex_df[["end", "filed", "form", "capital_expenditure"]],
        on=["end", "filed", "form"],
        how="outer",
    )

    # Add shares outstanding
    merged = merged.merge(
        shares_df[["end", "form", "shares_outstanding"]],
        on=["end", "form"],
        how="outer",
    ).sort_values(by=["end"])
    merged["shares_outstanding"] = merged["shares_outstanding"].ffill().bfill()
    merged = merged[(~merged["net_cashflow_ops"].isna())]
    merged = merged[(merged["form"] == "10-K")]
    merged["cik"] = str(company_facts.cik)
    merged["entityName"] = company_facts.entityName

    if str(company_facts.cik) in ticker_mapping:
        merged["ticker"] = ticker_mapping[str(company_facts.cik)]
    else:
        merged["ticker"] = None

    records = merged.to_dict(orient="records")

    return records


def process_directory(dir: str = None, output: str = "company_facts.jsonl"):
    """
    iterates through a list of json company facts files in a directory
    """

    if not os.path.isfile("ticker_mapping.pkl"):
        # create a cik number to ticker mapping first
        print("creating ticker mapping...")
        files = os.listdir(os.path.join(dir, "submissions"))
        ticker_cik_map = dict()
        for file in tqdm.tqdm(files):
            try:
                datum = load_json(os.path.join(dir, "submissions", file))
            except JSONDecodeError:
                continue
            if "tickers" not in datum:
                continue
            if len(datum["tickers"]) > 0:
                for ticker in datum["tickers"]:
                    ticker_cik_map[datum["cik"]] = ticker

        with open("ticker_mapping.pkl", "wb") as file:
            pickle.dump(ticker_cik_map, file)

    else:
        print("loading ticker mapping...")
        with open("ticker_mapping.pkl", "rb") as file:
            ticker_cik_map = pickle.load(file)

    # Now processing the Processing fillings
    files = os.listdir(os.path.join(dir, "companyfacts"))

    output_filepath = check_filepath(output)
    print(f"saving to file: {output_filepath}")

    for file in tqdm.tqdm(files):

        try:
            records = process_company_facts(
                os.path.join(dir, "companyfacts", file), ticker_mapping=ticker_cik_map
            )
            for record in records:
                json_line = json.dumps(record)

                with open(output_filepath, "a") as file:
                    file.write(json_line + "\n")
        except ValidationError:
            continue


if __name__ == "__main__":
    process_directory("data")
