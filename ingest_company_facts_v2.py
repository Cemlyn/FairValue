import os
import json
import pickle
from typing import List, Union

import tqdm
import pandas as pd
from pydantic import ValidationError

from fairvalue.utils import load_json
from fairvalue.models.ingestion_v2 import CompanyFacts, ParseException


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
    filepath: str,
    ticker_mapping: dict,
) -> List[
    Union[
        dict,
        None,
    ]
]:

    json_data = load_json(filepath)
    try:
        company_facts = CompanyFacts(**json_data)
    except ValidationError as e:
        raise ParseException(str(e))

    company_facts.__post_init_post_parse__()

    operating_cashflow_df = datum_to_dataframe(
        company_facts.operating_cashflow, "net_cashflow_ops"
    ).set_index("end")
    operating_cashflow_df = operating_cashflow_df[
        ~operating_cashflow_df["frame"].isna()
    ]

    shares_outstanding_df = datum_to_dataframe(
        company_facts.shares_outstanding_aligned, "shares_outstanding"
    ).set_index("end")
    shares_outstanding_df = shares_outstanding_df[
        ~shares_outstanding_df["frame"].isna()
    ]

    df = operating_cashflow_df.merge(shares_outstanding_df, on=["filed", "end", "form"])

    if company_facts.capital_expenditure:
        capital_expenditure_df = datum_to_dataframe(
            company_facts.capital_expenditure, "capital_expenditure"
        ).set_index("end")
        df = df.merge(capital_expenditure_df, on=["filed", "end", "form"], how="left")
        df["capital_expenditure"] = df["capital_expenditure"].fillna(0)
    else:
        df["capital_expenditure"] = 0

    df["cik"] = str(company_facts.cik)
    df["entityName"] = company_facts.entityName
    df["free_cashflow"] = df["net_cashflow_ops"] - df["capital_expenditure"]

    # fetching the ticker from the ticker mapping
    if str(company_facts.cik) in ticker_mapping:

        if "ticker_NYSE" in ticker_mapping[str(company_facts.cik)]:
            df["ticker_NYSE"] = ticker_mapping[str(company_facts.cik)]["ticker_NYSE"]

        if "ticker_Nasdaq" in ticker_mapping[str(company_facts.cik)]:
            df["ticker_Nasdaq"] = ticker_mapping[str(company_facts.cik)][
                "ticker_Nasdaq"
            ]

        df["ticker"] = ticker_mapping[str(company_facts.cik)]
    else:
        df["ticker"] = None

    records = df.to_dict(orient="records")

    return records


if __name__ == "__main__":

    OUTPUT = "company_facts.jsonl"
    DIR = "data"

    with open("ticker_mapping.pkl", "rb") as file:
        ticker_cik_map = pickle.load(file)

    # Now processing the Processing fillings and appending to jsonl files
    files = os.listdir(os.path.join(DIR, "companyfacts"))

    output_filepath = check_filepath(OUTPUT)

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
        except ParseException:
            continue
