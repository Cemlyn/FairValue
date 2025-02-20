import copy
import json
import datetime
from typing import List, Dict

import pandas as pd

from fairvalue.models.ingestion import SECFilings, Submissions, Datum
from fairvalue.models.financials import TickerFinancials
from fairvalue._exceptions import ParseException
from fairvalue.constants import (
    DATE_FORMAT,
    NET_CASHFLOW_OPS,
    CAPITAL_EXPENDITURE,
    SHARES_OUTSTANDING,
    STATE_OF_INCORP_DICT,
    FREE_CASHFLOW,
)


def fetch_state_dict():
    with open(STATE_OF_INCORP_DICT, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


state_dict = fetch_state_dict()


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


def check_for_foreign_currencies(sec_filing: SECFilings) -> bool:

    if (
        "USD"
        not in sec_filing.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units
    ):
        return True

    if (
        len(
            sec_filing.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units
        )
        > 1
    ):
        return True

    if (
        sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment
        is not None
    ):
        if (
            "USD"
            not in sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units
        ):
            return True
        if (
            len(
                sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units
            )
            > 1
        ):
            return True

    return False


def secfiling_to_financials(sec_filing: SECFilings) -> TickerFinancials:

    is_foreign = (
        not state_dict[sec_filing.submissions.stateOfIncorporationDescription]
    ) or check_for_foreign_currencies(sec_filing)

    if is_foreign:
        raise ParseException(
            "Company is foreign. Due to currency complications will not process this company for now."
        )

    state_currency = "USD"

    operating_cashflows = sec_filing.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
        state_currency
    ]

    if sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment:
        capital_expenditures = sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
            state_currency
        ]
    else:
        capital_expenditures = None

    shares_outstanding = (
        sec_filing.companyfacts.facts.dei.EntityCommonStockSharesOutstanding.units[
            "shares"
        ]
    )

    # If foreign need to convert shares outstanding into USD equivalent
    # For example,
    if is_foreign:
        if hasattr(
            sec_filing.companyfacts.facts.dei, "EntityListingDepositoryReceiptRatio"
        ) and hasattr(
            sec_filing.companyfacts.facts.dei.EntityListingDepositoryReceiptRatio,
            "units",
        ):
            adr_ratios = sec_filing.companyfacts.facts.dei.EntityListingDepositoryReceiptRatio.units[
                "pure"
            ]
        else:
            raise ParseException(
                "Could not find EntityListingDepositoryReceiptRatio in filing for foreign company."
            )

        shares_outstanding_adj = []

        for share_count in shares_outstanding:

            share_count_date = datetime.datetime.strptime(share_count.end, DATE_FORMAT)

            for n, adr_ratio in enumerate(adr_ratios):

                adr_ratio_date = datetime.datetime.strptime(adr_ratio.end, DATE_FORMAT)
                if adr_ratio_date > share_count_date:
                    break

            share_count_copy = copy.deepcopy(share_count)
            share_count_adj = share_count_copy.val / adr_ratios[n - 1].val
            share_count_copy.val = share_count_adj

            shares_outstanding_adj.append(share_count_copy)

        shares_outstanding = shares_outstanding_adj

    # Bringing shares outstanding inline with capex and cashflows
    shares_outstanding_aligned = []
    for op_cashflow in operating_cashflows:

        op_cashflow_date = datetime.datetime.strptime(op_cashflow.end, DATE_FORMAT)

        for n, share_count in enumerate(shares_outstanding):

            op_cf_date = datetime.datetime.strptime(share_count.end, DATE_FORMAT)
            if op_cf_date > op_cashflow_date:
                break

        op_cashflow_copy = copy.deepcopy(op_cashflow)
        op_cashflow_copy.val = shares_outstanding[n - 1].val

        shares_outstanding_aligned.append(op_cashflow_copy)

    latest_shares_outstanding = shares_outstanding[-1].val

    operating_cashflows_df = datum_to_dataframe(operating_cashflows, NET_CASHFLOW_OPS)

    if capital_expenditures:
        capital_expenditures_df = datum_to_dataframe(
            capital_expenditures, CAPITAL_EXPENDITURE
        )

    shares_outstanding_aligned_df = datum_to_dataframe(
        shares_outstanding_aligned, SHARES_OUTSTANDING
    )

    financials_df = operating_cashflows_df.merge(
        shares_outstanding_aligned_df[["filed", "end", "form", SHARES_OUTSTANDING]],
        on=["filed", "end", "form"],
    )

    if capital_expenditures:
        financials_df = financials_df.merge(
            capital_expenditures_df[["filed", "end", "form", CAPITAL_EXPENDITURE]],
            on=["filed", "end", "form"],
            how="left",
        )
    else:
        financials_df[CAPITAL_EXPENDITURE] = 0.00

    financials_df[CAPITAL_EXPENDITURE] = financials_df[CAPITAL_EXPENDITURE].astype(
        float
    )
    financials_df[CAPITAL_EXPENDITURE] = financials_df[CAPITAL_EXPENDITURE].fillna(0.0)
    financials_df[NET_CASHFLOW_OPS] = financials_df[NET_CASHFLOW_OPS].astype(float)
    financials_df[SHARES_OUTSTANDING] = financials_df[SHARES_OUTSTANDING].astype(int)

    financials_df["cik"] = sec_filing.companyfacts.cik
    ticker_and_exchange = search_ticker(sec_filing.submissions)
    financials_df["ticker"] = ticker_and_exchange["ticker"]
    financials_df["entityName"] = sec_filing.companyfacts.entityName
    financials_df["exchange"] = ticker_and_exchange["exchange"]
    financials_df["latest_shares_outstanding"] = latest_shares_outstanding
    financials_df["is_foreign"] = is_foreign
    financials_df["state_of_incorporation"] = (
        sec_filing.submissions.stateOfIncorporationDescription
    )

    return financials_df


def secfiling_to_annual_financials(sec_filing: SECFilings) -> TickerFinancials:

    financials_df = secfiling_to_financials(sec_filing=sec_filing)
    financials_df[CAPITAL_EXPENDITURE] = financials_df[CAPITAL_EXPENDITURE].fillna(0.0)
    financials_df[FREE_CASHFLOW] = (
        financials_df[NET_CASHFLOW_OPS] - financials_df[CAPITAL_EXPENDITURE]
    )
    financials_df["end_parsed"] = pd.to_datetime(
        financials_df["end"], format=DATE_FORMAT
    )
    financials_df["filed_parsed"] = pd.to_datetime(
        financials_df["filed"], format=DATE_FORMAT
    )
    financials_df["end_year"] = financials_df["end_parsed"].dt.year
    financials_df[SHARES_OUTSTANDING] = financials_df[SHARES_OUTSTANDING].abs()
    financials_df = financials_df[
        financials_df["form"].isin(["10-K", "20-F", "20-F/A", "10-K/A"])
    ]
    financials_df = financials_df.drop_duplicates(
        subset=["cik", "end_parsed", "filed_parsed"], keep="last"
    )
    financials_df = financials_df.drop_duplicates(
        subset=["cik", "end_year"], keep="last"
    )
    financials = TickerFinancials(**cfacts_df_to_dict(financials_df))

    return financials


def datum_to_dataframe(data: List[Datum], col_name: str) -> pd.DataFrame:
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


def search_ticker(submission: Submissions = None):

    if submission is None:
        raise ValueError("submission dict is None.")

    if len(submission.tickers) != len(submission.exchanges):
        raise ParseException(
            "Error search for ticker in Submission. 'tickers' and 'exchanges' values are different in length."
        )

    if (len(submission.tickers) == 0) or (len(submission.exchanges) == 0):
        raise ParseException(
            "Error search for ticker in Submission. Tickers and exchanges missing from submission."
        )

    for ticker, exchange in zip(submission.tickers, submission.exchanges):
        if (exchange is not None) and (exchange.lower() in ["nyse", "nasdaq"]):
            return {
                "ticker": ticker,
                "exchange": exchange,
            }

    """
    This section attempts to find the ticker that
    represents the common stock for companies which
    have multiple ticker associated with the company cik.
    For example, Ford Motor company has the ticker 'F' for 
    its common stock, and 'F-PC' for its debt securities.

    Typically the common stock ticker is the shortest.
    """
    shortest_ticker = None
    shortest_ticker_len = float("inf")
    shortest_ticker_exchange = None
    for i in range(len(submission.tickers)):

        if shortest_ticker is None:
            shortest_ticker = submission.tickers[i]
            shortest_ticker_len = len(shortest_ticker)
            shortest_ticker_exchange = submission.exchanges[i]

        elif len(submission.tickers[i]) < shortest_ticker_len:
            shortest_ticker = submission.tickers[i]
            shortest_ticker_len = len(shortest_ticker)
            shortest_ticker_exchange = submission.exchanges[i]

    return {
        "ticker": shortest_ticker,
        "exchange": shortest_ticker_exchange,
    }
