"""
Ingestion of Company Facts Script

This script processes SEC bulk companyfacts data, parsnig the json file data into 
a time ordered sturctured array which can be represented by a pandas dataframe. 

The script handles the following:

1. Loads companyfacts data files from a specified directory ('data/companyfacts').
2. Passes it to a pydantic data model to:
    - collect known items and verifiy their data types
    - align multiple times-series into a single times series, ie.:
        - net operating cash
        - capital expenditures
        - shares outstanding
        - if not present calculate a free cashflow

### Key Notes:
- The output is a jsonlines file called 'company_facts.jsonl'. Items in the file can 
    be easily passed to the 'Stock' class to run the discounted cashflow calculation.
- Is hard coded to only calculate times series on an annualised basis.

Ensure the `data/companyfacts` directory exists, where the companyfacts folder is the extracted
content of the bulk companyfacts.zip file which can be found 
on the SEC website: http://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip 
"""

import os
import json
import pickle
from typing import List, Union, Dict

import tqdm
import pandas as pd
from pydantic import ValidationError

from fairvalue.utils import load_json
from fairvalue.models.ingestion import CompanyFacts, ParseException
from fairvalue import Stock
from fairvalue.constants import DATE_FORMAT
from fairvalue.models.base import Floats, NonNegInts, Strs
from fairvalue.utils import series_to_list


def process_company_facts(
    filepath: str, ticker_mapping: dict
) -> List[Union[dict, None]]:

    try:
        json_data = load_json(filepath)
        company_facts = CompanyFacts(**json_data)
    except ValidationError as e:
        raise ParseException(e)

    df = company_facts.create_dataframe(ticker_mapping)

    # fetching the ticker from the ticker mapping
    cik_clean = str(company_facts.cik).lstrip("0")

    if cik_clean in ticker_mapping:
        df["ticker"] = ticker_mapping[cik_clean]["ticker"]
        df["exchange"] = ticker_mapping[cik_clean]["exchange"]

    else:
        df["ticker"] = None
        df["exchange"] = None

    records = df.to_dict(orient="records")

    return records


def cfacts_df_to_dict(df: pd.DataFrame) -> Dict[str, List]:

    company_facts = dict()
    company_facts["operating_cashflows"] = Floats(
        data=series_to_list(df.net_cashflow_ops.astype(float))
    )
    company_facts["capital_expenditures"] = Floats(
        data=series_to_list(df.capital_expenditure.astype(float))
    )
    company_facts["year_end_dates"] = Strs(data=series_to_list(df["end"]))
    company_facts["shares_outstanding"] = NonNegInts(
        data=series_to_list(df.shares_outstanding.astype(int))
    )

    if "free_cashflows" in df:

        company_facts["free_cashflows"] = Floats(
            data=series_to_list(df.free_cashflows.astype(float))
        )

    return company_facts


if __name__ == "__main__":

    DIR = "data"
    COMPANY_FACTS = "companyfacts"
    TICKER_DICT_FILENAME = "ticker_mapping.pkl"
    OUTPUT_FILE = "company_facts.jsonl"

    # Load the cik to ticker map
    with open(os.path.join(DIR, TICKER_DICT_FILENAME), "rb") as file:
        cik_2_ticker_map = pickle.load(file)

    # Process each of the json files in the company facts directory
    # appends to a json lines file
    if os.path.exists(os.path.join(DIR, OUTPUT_FILE)):
        os.remove(os.path.join(DIR, OUTPUT_FILE))

    for file in tqdm.tqdm(os.listdir(os.path.join(DIR, COMPANY_FACTS))):
        try:
            records = process_company_facts(
                os.path.join(DIR, COMPANY_FACTS, file), ticker_mapping=cik_2_ticker_map
            )
            if records:
                for record in records:
                    json_line = json.dumps(record)
                    with open(
                        os.path.join(DIR, OUTPUT_FILE), "a", encoding="utf-8"
                    ) as file:
                        file.write(json_line + "\n")
        except ParseException as e:
            continue
        except json.JSONDecodeError as e:
            continue

    """
    Load the pre-processed data into dataframe and passes
    the data to the Stock class which runs the discounted
    cashflow calculation using the default settings.
    """
    df = pd.read_json(os.path.join(DIR, "company_facts.jsonl"), lines=True)

    # for now we only consider annual reports - 10-Ks and 20-Fs plus any amendments
    df = df[df["form"].isin(["10-K", "10-K/A", "20-F", "20-F/A"])]
    df["end_parsed"] = pd.to_datetime(df["end"], format=DATE_FORMAT)
    df["filed_parsed"] = pd.to_datetime(df["filed"], format=DATE_FORMAT)
    df["end_year"] = df["end_parsed"].dt.year

    # fixing data errors
    mask = (df.cik == 889900) & (df.end == "2021-12-31") & (df.filed == "2024-02-27")
    df.loc[mask, "shares_outstanding"] = -df.loc[mask, "shares_outstanding"]
    mask = (df.cik == 889936) & (df.end == "2010-12-31") & (df.filed == "2013-02-22")
    df.loc[mask, "shares_outstanding"] = -df.loc[mask, "shares_outstanding"]
    df["shares_outstanding"] = df["shares_outstanding"].abs()

    # take the latest filed vesion of any reports within the financial year
    df = df.drop_duplicates(subset=["cik", "end_parsed", "filed_parsed"], keep="last")
    df = df.drop_duplicates(subset=["cik", "end_year"], keep="last")

    # looping through each cik company and running the dcf calculation
    count = 0
    stocks = []
    for cik_id, cik_df in df.groupby("cik"):

        cik_data = cfacts_df_to_dict(cik_df)
        entity_name = cik_df.loc[:, "entityName"].iloc[0]
        cik = cik_df.loc[:, "cik"].iloc[0]

        stock = Stock(
            ticker_id=cik_df.loc[:, "ticker"].iloc[0],
            cik=str(cik),
            exchange=cik_df.loc[:, "exchange"].iloc[0],
            entityName=entity_name,
            historical_financials=cik_data,
            latest_shares_outstanding=cik_df.loc[:, "latest_shares_outstanding"].iloc[
                0
            ],
        )

        stocks.append(stock.predict_fairvalue(historical_features=False))

    pd.DataFrame(stocks).sort_values(by=["last_filing_date"], ascending=False).to_csv(
        os.path.join(DIR, "intrinsic_value.csv"), index=False
    )
