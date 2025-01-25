import os
import warnings
from typing import (
    List,
    Union,
)
import pickle
import json
from json import JSONDecodeError
from collections import defaultdict

import tqdm
import pandas as pd
from pydantic import ValidationError

from fairvalue.utils import (
    load_json,
)
from fairvalue.models.ingestion import (
    CompanyFacts,
)
from fairvalue.constants import (
    DATE_FORMAT,
)
from fairvalue import (
    Stock,
    cfacts_df_to_dict,
)


def check_filepath(
    filepath: str,
) -> str:
    if os.path.isfile(filepath):
        return check_filepath(f"{filepath}.out")
    return filepath


def datum_to_dataframe(
    data,
    col_name,
):
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
    filepath: str,
    ticker_mapping: dict,
) -> List[
    Union[
        dict,
        None,
    ]
]:
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
        shares_df = datum_to_dataframe(
            shares,
            "shares_outstanding",
        )
        shares_df = shares_df[~shares_df["frame"].isna()]

    # if company_facts.facts.us_gaap.SharesOutstanding:
    #     shares = company_facts.facts.us_gaap.SharesOutstanding.units.shares
    #     shares_df = datum_to_dataframe(shares, "shares_outstanding")
    #     shares_df = shares_df[~shares_df["frame"].isna()]
    else:
        shares_df = pd.DataFrame(
            columns=[
                "end",
                "filed",
                "form",
                "shares_outstanding",
            ]
        )

    if company_facts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities:
        netcashflow = (
            company_facts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units.USD
        )
        netcashflow_df = datum_to_dataframe(
            netcashflow,
            "net_cashflow_ops",
        )
        netcashflow_df = netcashflow_df[~netcashflow_df["frame"].isna()]
    else:
        netcashflow_df = pd.DataFrame(
            columns=[
                "end",
                "filed",
                "form",
                "net_cashflow_ops",
            ]
        )

    if company_facts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment:
        capex = (
            company_facts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units.USD
        )
        capex_df = datum_to_dataframe(
            capex,
            "capital_expenditure",
        )
        capex_df = capex_df[~capex_df["frame"].isna()]
    else:
        capex_df = pd.DataFrame(
            columns=[
                "end",
                "filed",
                "form",
                "capital_expenditure",
            ]
        )

    # Combine cashflow and capex
    merged = netcashflow_df[
        [
            "end",
            "filed",
            "form",
            "net_cashflow_ops",
        ]
    ].merge(
        capex_df[
            [
                "end",
                "filed",
                "form",
                "capital_expenditure",
            ]
        ],
        on=[
            "end",
            "filed",
            "form",
        ],
        how="outer",
    )

    # merging on shares outstanding
    merged["end_ts"] = pd.to_datetime(
        merged["end"],
        format=DATE_FORMAT,
    )
    shares_df["end_ts"] = pd.to_datetime(shares_df["end"])

    def find_latest_shares_outstanding(
        row,
        shares,
    ):

        date = row["end_ts"]
        filtered = shares[shares["end_ts"] <= date]

        if not filtered.empty:
            latest_shares_outstanding = filtered["shares_outstanding"].iloc[-1]
        elif not shares.empty:
            latest_shares_outstanding = shares["shares_outstanding"].iloc[0]
        else:
            latest_shares_outstanding = None
        return latest_shares_outstanding

    if merged.empty:
        warnings.warn(
            "No full year financials.",
            category=UserWarning,
        )
        return None

    merged["shares_outstanding"] = merged.apply(
        lambda row: find_latest_shares_outstanding(
            row,
            shares_df,
        ),
        axis=1,
    )

    merged.drop(
        columns=["end_ts"],
        inplace=True,
    )

    merged["shares_outstanding"] = merged["shares_outstanding"].ffill().bfill()
    merged = merged[(~merged["net_cashflow_ops"].isna())]
    merged = merged[
        (
            merged["form"].isin(
                [
                    "10-K",
                    # "6-K",
                    "20-F",
                ]
            )
        )
    ]
    merged["cik"] = str(company_facts.cik)
    merged["entityName"] = company_facts.entityName

    if str(company_facts.cik) in ticker_mapping:

        if "ticker_NYSE" in ticker_mapping[str(company_facts.cik)]:
            merged["ticker_NYSE"] = ticker_mapping[str(company_facts.cik)][
                "ticker_NYSE"
            ]

        if "ticker_Nasdaq" in ticker_mapping[str(company_facts.cik)]:
            merged["ticker_Nasdaq"] = ticker_mapping[str(company_facts.cik)][
                "ticker_Nasdaq"
            ]

        merged["ticker"] = ticker_mapping[str(company_facts.cik)]
    else:
        merged["ticker"] = None

    records = merged.to_dict(orient="records")

    return records


if __name__ == "__main__":

    OUTPUT = "company_facts.jsonl"
    DIR = "data"

    # create a cik number to ticker mapping first
    if not os.path.isfile("ticker_mapping.pkl"):

        print("creating ticker mapping...")
        files = os.listdir(os.path.join(DIR, "submissions"))
        ticker_cik_map = dict()
        for file in tqdm.tqdm(files):
            try:
                datum = load_json(os.path.join(DIR, "submissions", file))
            except JSONDecodeError:
                continue
            if "tickers" not in datum:
                continue
            if len(datum["tickers"]) > 0:
                for ticker in datum["tickers"]:
                    ticker_cik_map[datum["cik"]] = ticker

            if ("tickers" in datum) and ("exchanges" in datum):
                if (len(datum["tickers"]) > 0) and (len(datum["exchanges"]) > 0):

                    ticker_dict = dict()
                    for ticker, exchange in zip(datum["tickers"], datum["exchanges"]):
                        ticker_dict[f"ticker_{exchange}"] = ticker

                    ticker_cik_map[datum["cik"]] = ticker_dict

        with open("ticker_mapping.pkl", "wb") as file:
            pickle.dump(ticker_cik_map, file)

    else:
        print("loading ticker mapping...")
        with open("ticker_mapping.pkl", "rb") as file:
            ticker_cik_map = pickle.load(file)

    # Now processing the Processing fillings and appending to jsonl files
    files = os.listdir(os.path.join(DIR, "companyfacts"))

    output_filepath = check_filepath(OUTPUT)
    print(f"saving to file: {output_filepath}")

    unable_to_parse_count = 0

    for file in tqdm.tqdm(files):

        try:
            records = process_company_facts(
                os.path.join(DIR, "companyfacts", file), ticker_mapping=ticker_cik_map
            )
            if records:
                for record in records:
                    json_line = json.dumps(record)
                    with open(output_filepath, "a", encoding="utf-8") as file:
                        file.write(json_line + "\n")
            else:
                unable_to_parse_count += 1
        except ValidationError:
            continue

    # print(f"Unable to parse: {unable_to_parse_count} out of {len(files)}")

    # creates a csv containing the predictions
    # df = pd.read_json(
    #     os.path.join(
    #         "data",
    #         "company_facts.jsonl",
    #     ),
    #     lines=True,
    # )
    # df["capital_expenditure"] = df["capital_expenditure"].fillna(0)
    # df["free_cashflows"] = df["net_cashflow_ops"] - df["capital_expenditure"]
    # df["end_parsed"] = pd.to_datetime(
    #     df["end"],
    #     format=DATE_FORMAT,
    # )
    # df["filed_parsed"] = pd.to_datetime(
    #     df["filed"],
    #     format=DATE_FORMAT,
    # )
    # df["end_year"] = df["end_parsed"].dt.year

    # # fixing data errors
    # mask = (df.cik == 889900) & (df.end == "2021-12-31") & (df.filed == "2024-02-27")
    # df.loc[
    #     mask,
    #     "shares_outstanding",
    # ] = -df.loc[
    #     mask,
    #     "shares_outstanding",
    # ]

    # mask = (df.cik == 889936) & (df.end == "	2010-12-31") & (df.filed == "2013-02-22")
    # df.loc[
    #     mask,
    #     "shares_outstanding",
    # ] = -df.loc[
    #     mask,
    #     "shares_outstanding",
    # ]

    # df["shares_outstanding"] = df["shares_outstanding"].abs()

    # df = df.drop_duplicates(
    #     subset=[
    #         "cik",
    #         "end_parsed",
    #         "filed_parsed",
    #     ],
    #     keep="last",
    # )

    # df = df.drop_duplicates(
    #     subset=[
    #         "cik",
    #         "end_year",
    #     ],
    #     keep="last",
    # )

    # count = 0
    # stocks = []
    # for (
    #     cik_id,
    #     cik_df,
    # ) in df.groupby("cik"):

    #     cik_data = cfacts_df_to_dict(cik_df)

    #     if ("ticker_Nasdaq" in cik_df) and not pd.isnull(
    #         cik_df.loc[:, "ticker_Nasdaq"].iloc[0]
    #     ):
    #         ticker_id = cik_df.loc[
    #             :,
    #             "ticker_Nasdaq",
    #         ].iloc[0]
    #         exchange = "NASDAQ"

    #     elif ("ticker_NYSE" in cik_df) and not pd.isnull(
    #         cik_df.loc[:, "ticker_NYSE"].iloc[0]
    #     ):
    #         ticker_id = cik_df.loc[
    #             :,
    #             "ticker_NYSE",
    #         ].iloc[0]
    #         exchange = "NYSE"

    #     elif ("ticker_CBOE" in cik_df) and not pd.isnull(
    #         cik_df.loc[:, "ticker_CBOE"].iloc[0]
    #     ):
    #         ticker_id = cik_df.loc[
    #             :,
    #             "ticker_CBOE",
    #         ].iloc[0]
    #         exchange = "CBOE"

    #     entity_name = cik_df.loc[
    #         :,
    #         "entityName",
    #     ].iloc[0]
    #     cik = cik_df.loc[
    #         :,
    #         "cik",
    #     ].iloc[0]

    #     stock = Stock(
    #         ticker_id=ticker_id,
    #         cik=str(cik),
    #         exchange=exchange,
    #         entityName=entity_name,
    #         historical_financials=cik_data,
    #     )

    #     stocks.append(stock.predict_fairvalue(historical_features=False))

    # pd.DataFrame(stocks).sort_values(
    #     by=["last_filing_date"],
    #     ascending=False,
    # ).to_csv(
    #     os.path.join(
    #         DIR,
    #         "intrinsic_value.csv",
    #     ),
    #     index=False,
    # )
