"""
Calculate Intrinsic Value

This script takes the ingested SEC filings in the form of the companyfacts.jsonl
file and passes it to the fairvalue.Stock class which is used to run the discounted
freecashflow calculation.
"""

import os
import csv
from typing import Dict, List

import pandas as pd

from fairvalue import Stock
from fairvalue.utils import series_to_list
from fairvalue.models.base import Floats, Strs, NonNegInts, NonNegFloats
from fairvalue.constants import (
    DATE_FORMAT,
    CAPITAL_EXPENDITURE,
    NET_CASHFLOW_OPS,
    FREE_CASHFLOW,
    SHARES_OUTSTANDING,
)
from logger_conf import get_logger

from fairvalue._exceptions import FairValueException

logger = get_logger("ingestion")

DIR = "data"


def cfacts_df_to_dict(df: pd.DataFrame) -> Dict[str, List]:

    company_facts = dict()
    company_facts[NET_CASHFLOW_OPS] = Floats(
        data=series_to_list(df.net_cashflow_ops.astype(float))
    )
    company_facts[CAPITAL_EXPENDITURE] = NonNegFloats(
        data=series_to_list(df.capital_expenditure.astype(float))
    )
    company_facts["year_end_dates"] = Strs(data=series_to_list(df["end"]))
    company_facts[SHARES_OUTSTANDING] = NonNegInts(
        data=series_to_list(df.shares_outstanding.astype(int))
    )

    if "free_cashflows" in df:

        company_facts["free_cashflows"] = Floats(
            data=series_to_list(df.free_cashflows.astype(float))
        )

    return company_facts


if __name__ == "__main__":

    df = pd.read_json(os.path.join("data", "company_facts.jsonl"), lines=True)
    df[CAPITAL_EXPENDITURE] = df[CAPITAL_EXPENDITURE].fillna(0)
    df[FREE_CASHFLOW] = df[NET_CASHFLOW_OPS] - df[CAPITAL_EXPENDITURE]
    df["end_parsed"] = pd.to_datetime(df["end"], format=DATE_FORMAT)
    df["filed_parsed"] = pd.to_datetime(df["filed"], format=DATE_FORMAT)
    df["end_year"] = df["end_parsed"].dt.year

    # fixing data errors
    mask = (df.cik == 889900) & (df.end == "2021-12-31") & (df.filed == "2024-02-27")
    df.loc[mask, SHARES_OUTSTANDING] = -df.loc[mask, SHARES_OUTSTANDING]

    mask = (df.cik == 889936) & (df.end == "2010-12-31") & (df.filed == "2013-02-22")
    df.loc[mask, SHARES_OUTSTANDING] = -df.loc[mask, SHARES_OUTSTANDING]

    df[SHARES_OUTSTANDING] = df[SHARES_OUTSTANDING].abs()

    df = df[df["form"].isin(["10-K", "20-F", "20-F/A", "10-K/A"])]

    df = df.drop_duplicates(subset=["cik", "end_parsed", "filed_parsed"], keep="last")
    df = df.drop_duplicates(subset=["cik", "end_year"], keep="last")

    count = 0
    stocks = []
    for cik_id, cik_df in df.groupby("cik"):

        try:
            stock = Stock(
                ticker_id=cik_df.loc[:, "ticker"].iloc[0],
                exchange=cik_df.loc[:, "exchange"].iloc[0],
                cik=str(cik_df.loc[:, "cik"].iloc[0]),
                latest_shares_outstanding=cik_df.loc[
                    :, "latest_shares_outstanding"
                ].iloc[0],
                entity_name=cik_df.loc[:, "entityName"].iloc[0],
                historical_financials=cfacts_df_to_dict(cik_df),
            )

            intrinsic_value = stock.predict_fairvalue(
                growth_rate=0.0,
                growth_decay_rate=0.01,
                discounting_rate=0.05,
                number_of_years=10,
            )
            stocks.append(intrinsic_value)

        except FairValueException as e:
            print(f"Skipped!, {e}")

    # import json
    # with open('test.json','w') as file:
    #     json.dump(stocks,file)

    df = pd.DataFrame(stocks)  # .sort_values(by=["last_filing_date"], ascending=False)
    # columns = df.columns.tolist()
    # priority_cols = [
    #     "ticker_id",
    #     "entity_name",
    #     "cik",
    #     "exchange",
    #     "shares_outstanding",
    #     "latest_free_cashflow",
    #     "company_value",
    #     "intrinsic_value",
    #     "last_filing_date",
    # ]
    # other_cols = [x for x in columns if x not in priority_cols]
    # df[priority_cols + other_cols].to_csv(
    #     os.path.join(DIR, "intrinsic_value.csv"), index=False, quoting=csv.QUOTE_MINIMAL
    # )
    df.to_csv(
        os.path.join(DIR, "intrinsic_value.csv"), index=False, quoting=csv.QUOTE_MINIMAL
    )
