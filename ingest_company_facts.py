import os
import json
from json import JSONDecodeError
import pickle
from typing import List, Union, Dict

import tqdm
import pandas as pd
import numpy as np
from pydantic import ValidationError

from fairvalue.utils import load_json, series_to_list
from fairvalue.models.ingestion import CompanyFacts, ParseException
from fairvalue import Stock
from fairvalue.constants import DATE_FORMAT
from fairvalue.models.base import Floats, Strs, NonNegFloats, NonNegInts


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


def check_filepath(filepath: str) -> str:
    if os.path.isfile(filepath):
        return check_filepath(f"{filepath}.out")
    return filepath


def datum_to_dataframe(data, col_name):
    return pd.DataFrame(
        [
            {
                "end": datum.end,
                "accn": datum.accn,
                "form": datum.form,
                "filed": datum.filed,
                "frame": datum.frame,
                col_name: datum.val,
            }
            for datum in data
        ]
    )


def process_company_facts(
    filepath: str, ticker_mapping: dict
) -> List[Union[dict, None]]:

    json_data = load_json(filepath)
    try:
        company_facts = CompanyFacts(**json_data)
    except ValidationError as e:
        raise ParseException(str(e))

    company_facts.__post_init_post_parse__()

    operating_cashflow_df = datum_to_dataframe(
        company_facts.operating_cashflow, "net_cashflow_ops"
    )
    operating_cashflow_df = operating_cashflow_df[
        ~operating_cashflow_df["frame"].isna()
    ]

    shares_outstanding_df = datum_to_dataframe(
        company_facts.shares_outstanding_aligned, "shares_outstanding"
    )
    shares_outstanding_df = shares_outstanding_df[
        ~shares_outstanding_df["frame"].isna()
    ]

    df = operating_cashflow_df.merge(
        shares_outstanding_df[["filed", "end", "form", "shares_outstanding"]],
        on=["filed", "end", "form"],
    )

    if company_facts.capital_expenditure:
        capital_expenditure_df = datum_to_dataframe(
            company_facts.capital_expenditure, "capital_expenditure"
        )
        df = df.merge(
            capital_expenditure_df[["filed", "end", "form", "capital_expenditure"]],
            on=["filed", "end", "form"],
            how="left",
        )
        df["capital_expenditure"] = df["capital_expenditure"].fillna(0)
    else:
        df["capital_expenditure"] = 0

    df["cik"] = str(company_facts.cik)
    df["entityName"] = company_facts.entityName
    df["free_cashflows"] = df["net_cashflow_ops"] - df["capital_expenditure"]

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


def search_ticker(submission: dict) -> Dict[str, str]:

    empty_response = {"ticker": None, "exchange": None}

    if len(submission["tickers"]) != len(submission["exchanges"]):
        raise ParseException("cannot create ticker for....")

    if ("tickers" not in submission) or ("exchanges" not in submission):
        return empty_response

    if (len(submission["tickers"]) == 0) or (len(submission["exchanges"]) == 0):
        return empty_response

    for ticker, exchange in zip(submission["tickers"], submission["exchanges"]):
        if (exchange is not None) and (exchange.lower() in ["nyse", "nasdaq"]):
            return {"ticker": ticker, "exchange": exchange}

    # If still not found take the shortest
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

    OUTPUT = "company_facts.jsonl"
    DIR = "data"
    TICKER_DICT_FILENAME = "ticker_mapping.pkl"
    SUBMISSIONS = "submissions"

    TICKER_DICT_FILEPATH = os.path.join(DIR, TICKER_DICT_FILENAME)

    # create a cik number to ticker mapping first
    # if not os.path.isfile(TICKER_DICT_FILEPATH):

    #     files = os.listdir(os.path.join(DIR, SUBMISSIONS))

    #     ticker_dict = dict()
    #     for file in tqdm.tqdm(files):
    #         try:
    #             submission = load_json(os.path.join(DIR, "submissions", file))
    #         except json.JSONDecodeError:
    #             continue
    #         if ("cik" not in submission) or (submission["cik"] is None):
    #             continue
    #         cik = str(submission["cik"]).lstrip("0")
    #         ticker_dict[cik] = search_ticker(submission)

    #     with open(TICKER_DICT_FILEPATH, "wb") as file:
    #         pickle.dump(ticker_dict, file)

    # else:
    #     with open(TICKER_DICT_FILEPATH, "rb") as file:
    #         ticker_cik_map = pickle.load(file)

    # Now processing the Processing fillings and appending to jsonl files
    # files = os.listdir(os.path.join(DIR, "companyfacts"))

    # output_filepath = check_filepath(OUTPUT)

    # for file in tqdm.tqdm(files):
    #     try:
    #         records = process_company_facts(
    #             os.path.join(DIR, "companyfacts", file), ticker_mapping=ticker_cik_map
    #         )
    #         if records:
    #             for record in records:
    #                 json_line = json.dumps(record)
    #                 with open(output_filepath, "a", encoding="utf-8") as file:
    #                     file.write(json_line + "\n")
    #     except ParseException:
    #         continue
    #     except KeyError:
    #         continue

    # creates a csv containing the predictions
    df = pd.read_json(os.path.join(DIR, "company_facts.jsonl"), lines=True)
    df = df[df["form"].isin(["10-K", "10-K/A", "20-F", "20-F/A"])]
    df["end_parsed"] = pd.to_datetime(df["end"], format=DATE_FORMAT)
    df["filed_parsed"] = pd.to_datetime(df["filed"], format=DATE_FORMAT)
    df["end_year"] = df["end_parsed"].dt.year

    # fixing data errors
    mask = (df.cik == 889900) & (df.end == "2021-12-31") & (df.filed == "2024-02-27")
    df.loc[mask, "shares_outstanding"] = -df.loc[mask, "shares_outstanding"]

    mask = (df.cik == 889936) & (df.end == "	2010-12-31") & (df.filed == "2013-02-22")
    df.loc[mask, "shares_outstanding"] = -df.loc[mask, "shares_outstanding"]

    df["shares_outstanding"] = df["shares_outstanding"].abs()

    df = df.drop_duplicates(subset=["cik", "end_parsed", "filed_parsed"], keep="last")
    df = df.drop_duplicates(subset=["cik", "end_year"], keep="last")

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
        )

        stocks.append(stock.predict_fairvalue(historical_features=False))

    pd.DataFrame(stocks).sort_values(by=["last_filing_date"], ascending=False).to_csv(
        os.path.join(DIR, "intrinsic_value.csv"), index=False
    )
