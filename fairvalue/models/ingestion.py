import copy
import json
from datetime import datetime
from typing import List, Optional, Union, Literal, Dict

import pandas as pd

from pydantic import BaseModel, Field, field_validator
from fairvalue.models.utils import validate_date
from fairvalue.constants import STATE_OF_INCORP_DICT, DATE_FORMAT


def fetch_state_dict():
    with open(STATE_OF_INCORP_DICT, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


state_dict = fetch_state_dict()
states_list = list(state_dict.keys())


class Datum(BaseModel):
    """
    - 10-k: annual financial report
    - 20-F: financial filing that non-U.S. companies (foreign private issuers)
    - 6-K:  interim reports or disclose material information that occurs between the company’s annual filings
        for foreign private issuers whose securities are traded on U.S. exchanges.
    - 20-F/A: amended version of a 20-F filing
    - 10-Q: 10-Q is a quarterly financial report that publicly traded companies in the United States
    """

    end: str  # Must be a valid date
    val: Union[int, float]
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
    cik: Union[str, int]
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
    cik: Union[str, int]
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
        companyfacts: Union[CompanyFacts, str],
        submissions: Union[Submissions, str],
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
