import copy
import json
from datetime import datetime
from typing import List, Optional, Literal, Dict

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from fairvalue.models.financials import TickerFinancials
from fairvalue._exceptions import ParseException
from fairvalue.models.utils import validate_date
from fairvalue.constants import (
    STATE_OF_INCORP_DICT,
    DATE_FORMAT,
    CAPITAL_EXPENDITURE,
    FREE_CASHFLOW,
    SHARES_OUTSTANDING,
    NET_CASHFLOW_OPS,
)


def fetch_state_dict():
    with open(STATE_OF_INCORP_DICT, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


state_dict = fetch_state_dict()
states_list = list(state_dict.keys())


# =============================================================================
# pydantic models used to ingest SEC filings
# =============================================================================


class Datum(BaseModel):
    """
    - 10-k: annual financial report
    - 20-F: financial filing that non-U.S. companies (foreign private issuers)
    - 6-K:  interim reports or disclose material information that occurs between the company's annual filings
        for foreign private issuers whose securities are traded on U.S. exchanges.
    - 20-F/A: amended version of a 20-F filing
    - 10-Q: 10-Q is a quarterly financial report that publicly traded companies in the United States
    """

    end: str  # Must be a valid date
    val: int | float
    accn: Optional[str] = None
    fy: Optional[int] = None
    fp: Optional[str] = None
    form: Literal["10-K", "20-F", "6-K", "20-F/A", "10-Q", "10-Q/A", "10-K/A", "8-K"]
    filed: str  # Must be a valid date
    frame: Optional[str] = None

    @field_validator("end", "filed", mode="before")
    @classmethod
    def validate_end(cls, value, info):
        return validate_date(info.field_name, value)


class FinancialMetric(BaseModel):
    label: str
    description: str
    units: Dict[str, List[Datum]]
    model_config = {"extra": "allow"}

    @field_validator("units", mode="before")
    def validate_currency_data(cls, value):
        if not isinstance(value, dict):
            raise ValueError(
                "currency_data must be a dictionary with currency codes as keys."
            )
        for currency, data in value.items():
            if not isinstance(data, list) or len(data) == 0:
                raise ValueError(
                    f"The '{currency}' field must contain at least one entry."
                )
        return value


class USGaap(BaseModel):
    NetCashProvidedByUsedInOperatingActivities: FinancialMetric
    CommonStockSharesOutstanding: FinancialMetric
    StockholdersEquityNoteStockSplitConversionRatio1: Optional[FinancialMetric] = None
    PaymentsToAcquirePropertyPlantAndEquipment: Optional[FinancialMetric] = None
    model_config = {"extra": "allow"}

    @field_validator("NetCashProvidedByUsedInOperatingActivities", mode="after")
    @classmethod
    def convert_to_float(cls, value):
        """Ensure this value is always a float."""
        if isinstance(value, FinancialMetric):
            for currency, data_list in value.units.items():
                for datum in data_list:
                    datum.val = float(datum.val)  # Convert to float
        return value

    @field_validator("PaymentsToAcquirePropertyPlantAndEquipment", mode="after")
    @classmethod
    def convert_to_non_negative_float(cls, value):
        """Ensure this value is always a non-negative float."""
        if value is not None and isinstance(value, FinancialMetric):
            for currency, data_list in value.units.items():
                for datum in data_list:
                    datum.val = max(
                        0.0, float(datum.val)
                    )  # Convert to float and enforce non-negativity
        return value


class Dei(BaseModel):
    EntityCommonStockSharesOutstanding: FinancialMetric
    EntityPublicFloat: Optional[FinancialMetric] = None
    EntityListingDepositoryReceiptRatio: Optional[FinancialMetric] = None
    model_config = {"extra": "allow"}

    @field_validator("EntityCommonStockSharesOutstanding", mode="after")
    @classmethod
    def convert_to_non_negative_int(cls, value):
        """Ensure this value is always a non-negative float."""
        if value is not None and isinstance(value, FinancialMetric):
            for currency, data_list in value.units.items():
                for datum in data_list:
                    if datum.val < 0:
                        raise ValueError("Negative shares outstanding are not allowed.")
                    datum.val = max(
                        0, int(datum.val)
                    )  # Convert to float and enforce non-negativity
        return value


class Facts(BaseModel):
    dei: Dei
    us_gaap: USGaap = Field(alias="us-gaap")


class RecentFilings(BaseModel):
    filingDate: List[str] = Field(
        ..., description="List of filing dates in YYYY-MM-DD format"
    )

    @field_validator("filingDate", mode="before")
    def validate_date_format(cls, values):
        """Ensures that all dates in the list are in YYYY-MM-DD format."""
        if not isinstance(values, list):
            raise TypeError(
                f"Expected a list of dates, but got {type(values).__name__}"
            )

        for date in values:
            if not isinstance(date, str):
                raise TypeError(
                    f"Expected a string for date, but got {type(date).__name__}: {date}"
                )

            try:
                datetime.strptime(date, DATE_FORMAT)
            except ValueError:
                raise ValueError(
                    f"Invalid date format: {date}. Expected format: YYYY-MM-DD"
                )

        return values  # Return the validated list


class Filings(BaseModel):
    recent: RecentFilings


class Submissions(BaseModel):
    cik: str | int
    entityType: Optional[str] = None
    sic: Optional[str] = None
    sicDescription: Optional[str] = None
    name: Optional[str] = None
    tickers: List[str]
    exchanges: List[str]
    filings: Filings
    stateOfIncorporationDescription: Literal[
        "AK",
        "AL",
        "AR",
        "AZ",
        "Alberta, Canada",
        "Anguilla",
        "Antigua and Barbuda",
        "Argentina",
        "Australia",
        "Bahamas",
        "Belgium",
        "Bermuda",
        "Brazil",
        "British Columbia, Canada",
        "British Indian Ocean Territory",
        "CA",
        "CO",
        "CT",
        "Canada (Federal Level)",
        "Cayman Islands",
        "Chile",
        "China",
        "Colombia",
        "Cyprus",
        "DC",
        "DE",
        "Denmark",
        "FL",
        "Finland",
        "France",
        "GA",
        "Germany",
        "Gibraltar",
        "Grenada",
        "Guam",
        "Guernsey",
        "HI",
        "Hong Kong",
        "IA",
        "ID",
        "IL",
        "IN",
        "India",
        "Ireland",
        "Isle of Man",
        "Israel",
        "Italy",
        "Japan",
        "Jersey",
        "KS",
        "KY",
        "Kazakhstan",
        "Korea, Republic of",
        "LA",
        "Luxembourg",
        "MA",
        "MD",
        "ME",
        "MI",
        "MN",
        "MO",
        "MS",
        "MT",
        "Malaysia",
        "Manitoba, Canada",
        "Marshall Islands",
        "Mauritius",
        "Mexico",
        "NC",
        "ND",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NV",
        "NY",
        "Netherlands",
        "Netherlands Antilles",
        "New Brunswick, Canada",
        "New Zealand",
        "Newfoundland, Canada",
        "Norway",
        "Nova Scotia, Canada",
        "OH",
        "OK",
        "OR",
        "Ontario, Canada",
        "PA",
        "Panama",
        "Peru",
        "Puerto Rico",
        "Quebec, Canada",
        "RI",
        "Russian Federation",
        "SC",
        "SD",
        "Singapore",
        "South Africa",
        "Spain",
        "Sweden",
        "Switzerland",
        "TN",
        "TX",
        "Taiwan, Province of China",
        "Turkey",
        "UT",
        "United Kingdom",
        "Unknown",
        "VA",
        "VT",
        "Virgin Islands, British",
        "Virgin Islands, U.S.",
        "WA",
        "WI",
        "WV",
        "WY",
        "X1",
        "Yukon, Canada",
    ]


class CompanyFacts(BaseModel):
    cik: str | int
    entityName: str
    facts: Facts

    @field_validator("cik", mode="after")
    @classmethod
    def convert_cik_to_str(cls, value):
        """Accept int or str, but always hold cik as string."""
        return str(value)


class SECFilingsModel(BaseModel):
    companyfacts: CompanyFacts
    submissions: Submissions


class SECFilings:

    def __init__(
        self,
        companyfacts: CompanyFacts | str,
        submissions: Submissions | str,
    ):

        if isinstance(companyfacts, str) or isinstance(submissions, str):

            if not (isinstance(companyfacts, str) and isinstance(submissions, str)):
                raise ValueError(
                    "Both companyfacts and submissions args must be str if either is str."
                )

            with open(companyfacts, encoding="utf-8", mode="r") as file:
                companyfacts_json = json.load(file)

            with open(submissions, encoding="utf-8", mode="r") as file:
                submissions_json = json.load(file)

            companyfacts = CompanyFacts(**companyfacts_json)
            submissions = Submissions(**submissions_json)

        self._instance = SECFilingsModel(
            companyfacts=companyfacts, submissions=submissions
        )

        self.date_of_latest_filing = self._extract_latest_filing_date(submissions)

    def _extract_latest_filing_date(self, submissions: Submissions) -> Optional[str]:
        """
        Extracts the most recent filing date from the 'RecentFilings' section.
        Returns the latest date as a string in 'YYYY-MM-DD' format.
        """
        try:
            report_dates = submissions.filings.recent.filingDate
            if report_dates:
                latest_date = max(
                    datetime.strptime(date, DATE_FORMAT) for date in report_dates
                )
                return latest_date.strftime(DATE_FORMAT)
        except Exception as e:
            print(f"Error extracting latest filing date: {e}")
        return None  # Return None if no valid date is found

    def __getattr__(self, name):
        """Redirects attribute access to the TargetModel instance."""
        return getattr(self._instance, name)

    def __repr__(self):
        """Returns the string representation of the TargetModel instance."""
        return repr(self._instance)

    def to_annual_financials(self, return_dataframe=False) -> TickerFinancials:
        """
        Transform SEC filing data into annual financial metrics.

        Returns:
            TickerFinancials: Annual financial metrics model
        """

        return secfiling_to_annual_financials(self, return_dataframe=return_dataframe)


# =============================================================================
# Functions used by pydantic models to ingest SEC filings
# =============================================================================


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


# for each stock split find the nearest month in which
def nearest(split_date: pd.Timestamp, dates: pd.Series):
    valid_dates = dates[dates <= split_date]

    if valid_dates.empty:
        return None

    return valid_dates.idxmax()


def secfiling_to_financials(sec_filing: SECFilings) -> pd.DataFrame:

    is_foreign = (
        not state_dict[sec_filing.submissions.stateOfIncorporationDescription]
    ) or check_for_foreign_currencies(sec_filing)

    if is_foreign:
        raise ParseException(
            "Company is foreign. Due to currency complications will not process this company for now."
        )

    state_currency = "USD"

    us_gaap = getattr(sec_filing.companyfacts.facts, "us_gaap", None)

    if not us_gaap:
        raise ParseException("Missing us_gaap data")
    if not hasattr(us_gaap, "NetCashProvidedByUsedInOperatingActivities"):
        raise ParseException("Missing NetCashProvidedByUsedInOperatingActivities data")
    if not hasattr(us_gaap, "PaymentsToAcquirePropertyPlantAndEquipment"):
        raise ParseException("Missing PaymentsToAcquirePropertyPlantAndEquipment data")
    if not hasattr(us_gaap, "CommonStockSharesOutstanding"):
        raise ParseException("Missing CommonStockSharesOutstanding data")

    operating_cashflows = sec_filing.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
        state_currency
    ]

    if sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment:
        capital_expenditures = sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
            state_currency
        ]
    else:
        capital_expenditures = None

    if (
        "shares"
        not in sec_filing.companyfacts.facts.us_gaap.CommonStockSharesOutstanding.units
    ):
        raise ParseException("shares missing from CommonStockSharesOutstanding")

    shares_outstanding = (
        sec_filing.companyfacts.facts.us_gaap.CommonStockSharesOutstanding.units[
            "shares"
        ]
    )

    shares_outstanding_df = datum_to_dataframe(shares_outstanding, SHARES_OUTSTANDING)
    shares_outstanding_df["end_parsed"] = pd.to_datetime(shares_outstanding_df["end"])
    shares_outstanding_df["filed_parsed"] = pd.to_datetime(
        shares_outstanding_df["filed"]
    )

    # logic to handle stock split. If a filing for an end date which preceded the stock split
    # is filed after the split, it seems that the new shares outstanding is used in the new filing
    # causing a historic datapoint to look like the split has already occurred.
    if (
        sec_filing.companyfacts.facts.us_gaap.StockholdersEquityNoteStockSplitConversionRatio1
    ):

        if (
            "pure"
            not in sec_filing.companyfacts.facts.us_gaap.StockholdersEquityNoteStockSplitConversionRatio1.units
        ):
            raise ParseException(
                "pure missing from StockholdersEquityNoteStockSplitConversionRatio1"
            )

        stock_split_conversions = sec_filing.companyfacts.facts.us_gaap.StockholdersEquityNoteStockSplitConversionRatio1.units[
            "pure"
        ]

        stock_split_df = datum_to_dataframe(stock_split_conversions, "stock_split")
        stock_split_df = stock_split_df[~stock_split_df["frame"].isna()].reset_index(
            drop=True
        )

        stock_split_df["end_parsed"] = pd.to_datetime(stock_split_df["end"])
        stock_split_df = stock_split_df.sort_values(by=["end_parsed"])

        # if stock split dates don't overlap with the shares outstanding dates, set all stock splits to 1
        if len(stock_split_df) == 0:
            shares_outstanding_df["stock_split"] = 1
            shares_outstanding_df["stock_split_date"] = None

        elif (
            stock_split_df["end_parsed"].max()
            < shares_outstanding_df["end_parsed"].min()
        ):
            shares_outstanding_df["stock_split"] = 1
            shares_outstanding_df["stock_split_date"] = None

        else:
            for _, row_df in stock_split_df.iterrows():
                nearest_date_index = nearest(
                    row_df["end_parsed"], shares_outstanding_df["end_parsed"]
                )

                if nearest_date_index is None:
                    continue

                shares_outstanding_df.loc[nearest_date_index, "stock_split"] = row_df[
                    "stock_split"
                ]
                shares_outstanding_df.loc[nearest_date_index, "stock_split_date"] = (
                    row_df["end_parsed"]
                )

            shares_outstanding_df["stock_split_date"] = shares_outstanding_df[
                "stock_split_date"
            ].bfill()

            shares_outstanding_df["stock_split"] = shares_outstanding_df[
                "stock_split"
            ].fillna(1)
            shares_outstanding_df["stock_split"] = shares_outstanding_df["stock_split"][
                ::-1
            ].cumprod()[::-1]

            # drop filings that are for financials before the stock split date but were filed after the stock split. In such cases the new filing contains shares outstanding after the split causing confusion.
            shares_outstanding_df = shares_outstanding_df[
                ~(
                    (
                        shares_outstanding_df["end_parsed"]
                        < shares_outstanding_df["stock_split_date"]
                    )
                    & (
                        shares_outstanding_df["stock_split_date"]
                        < shares_outstanding_df["filed_parsed"]
                    )
                )
            ]
    else:
        shares_outstanding_df["stock_split"] = 1
        shares_outstanding_df["stock_split_date"] = None

    # deduplicating to keep the latest filed 10-k or 20-k after the exclusions above
    shares_outstanding_df = shares_outstanding_df[
        shares_outstanding_df["form"].isin(["10-K", "20-F", "20-F/A", "10-K/A"])
    ]
    shares_outstanding_df = shares_outstanding_df.sort_values(
        by=["end_parsed", "filed_parsed"]
    )
    shares_outstanding_df = shares_outstanding_df.drop_duplicates(
        subset=["end_parsed"], keep="last"
    )

    shares_outstanding_df[SHARES_OUTSTANDING] = (
        shares_outstanding_df[SHARES_OUTSTANDING] * shares_outstanding_df["stock_split"]
    )
    shares_outstanding_df["form"] = "10-K"
    shares_outstanding_df = shares_outstanding_df[["end", "form", SHARES_OUTSTANDING]]

    latest_shares_outstanding = shares_outstanding_df.iloc[[-1]][SHARES_OUTSTANDING]

    operating_cashflows_df = datum_to_dataframe(operating_cashflows, NET_CASHFLOW_OPS)

    if capital_expenditures:
        capital_expenditures_df = datum_to_dataframe(
            capital_expenditures, CAPITAL_EXPENDITURE
        )

    financials_df = operating_cashflows_df.merge(
        shares_outstanding_df[["end", "form", SHARES_OUTSTANDING]],
        on=["end", "form"],
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
    financials_df[SHARES_OUTSTANDING] = financials_df[SHARES_OUTSTANDING].astype(float)

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


def secfiling_to_annual_financials(
    sec_filing: SECFilings,
    return_dataframe: bool = False,
    dates_as_string: bool = True,
) -> TickerFinancials | pd.DataFrame:
    """Transform SEC filing data into annual financial metrics.

    Args:
        sec_filing (SECFilings): SEC filing data
        return_dataframe (bool, optional): Whether to return a pandas DataFrame. Defaults to False.
        dates_as_string (bool, optional): Whether to return dates as strings or datetime objects. Defaults to True.

    Returns:
        Union[TickerFinancials, pd.DataFrame]: Financial data either as a TickerFinancials model or DataFrame
    """

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

    # Now handling everything else
    financials_df = financials_df[
        financials_df["form"].isin(["10-K", "20-F", "20-F/A", "10-K/A"])
    ]
    financials_df = financials_df.drop_duplicates(
        subset=["cik", "end_parsed", "filed_parsed"], keep="last"
    )
    financials_df = financials_df.drop_duplicates(
        subset=["cik", "end_year"], keep="last"
    )

    if return_dataframe:
        if dates_as_string:
            # Convert all datetime columns to strings using DATE_FORMAT
            datetime_cols = ["end_parsed", "filed_parsed", "stock_split_date"]
            for col in datetime_cols:
                if col in financials_df.columns:
                    financials_df[col] = financials_df[col].dt.strftime(DATE_FORMAT)

        return financials_df

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

        if (shortest_ticker is None) or (
            len(submission.tickers[i]) < shortest_ticker_len
        ):
            shortest_ticker = submission.tickers[i]
            shortest_ticker_len = len(shortest_ticker)
            shortest_ticker_exchange = submission.exchanges[i]

    return {
        "ticker": shortest_ticker,
        "exchange": shortest_ticker_exchange,
    }
