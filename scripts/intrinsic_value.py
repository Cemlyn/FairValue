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
from pydantic import ValidationError

from fairvalue import Stock
from fairvalue.constants import (
    DATE_FORMAT,
    CAPITAL_EXPENDITURE,
    NET_CASHFLOW_OPS,
    FREE_CASHFLOW,
    SHARES_OUTSTANDING,
)

from fairvalue._exceptions import FairValueException


DIR = "data"


def cfacts_df_to_dict(df: pd.DataFrame) -> Dict[str, List]:

    company_facts = dict()
    company_facts["operating_cashflows"] = df.net_cashflow_ops.astype(float).tolist()
    company_facts["capital_expenditures"] = df.capital_expenditure.astype(
        float
    ).tolist()
    company_facts["year_end_dates"] = df["end"].tolist()
    company_facts["shares_outstanding"] = df.shares_outstanding.astype(int).tolist()

    if "free_cashflows" in df:

        company_facts["free_cashflows"] = df.free_cashflows.astype(float).tolist()

    return company_facts


if __name__ == "__main__":

    df = pd.read_json(os.path.join("data", "company_facts.jsonl"), lines=True)
    df[CAPITAL_EXPENDITURE] = df[CAPITAL_EXPENDITURE].fillna(0.0)
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

    stocks = []
    for cik_id, cik_df in df.groupby("cik"):

        try:
            historical_finances = cfacts_df_to_dict(cik_df)

            stock = Stock(
                ticker_id=cik_df.loc[:, "ticker"].iloc[0],
                exchange=cik_df.loc[:, "exchange"].iloc[0],
                cik=str(cik_df.loc[:, "cik"].iloc[0]),
                latest_shares_outstanding=cik_df.loc[:, "shares_outstanding"].iloc[-1],
                entity_name=cik_df.loc[:, "entityName"].iloc[0],
                historical_financials=historical_finances,
            )

            intrinsic_value = stock.predict_fairvalue(
                growth_rate=0.02,
                discounting_rate=0.05,
                number_of_years=10,
                historical_features=True,
            )
            stocks.append(intrinsic_value)

        except FairValueException as e:
            print(f"FairValueException, {e}")
        except ValidationError as e:
            print(f"ValidationError, {e}")

    df = pd.DataFrame(stocks)
    df.to_csv(
        os.path.join(DIR, "intrinsic_value.csv"), index=False, quoting=csv.QUOTE_MINIMAL
    )
