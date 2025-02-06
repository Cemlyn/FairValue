import copy
import json
from datetime import datetime
from typing import List, Optional, Union, Literal, Dict

import pandas as pd

from pydantic import BaseModel, Field, field_validator
from fairvalue.models.utils import validate_date
from fairvalue.constants import STATE_OF_INCORP_DICT


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


# class USGaap(BaseModel):
#     NetCashProvidedByUsedInOperatingActivities: FinancialMetric
#     PaymentsToAcquirePropertyPlantAndEquipment: Optional[FinancialMetric] = None
#     model_config = {"extra": "allow"}


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


class Facts(BaseModel):
    dei: Dei
    us_gaap: USGaap = Field(alias="us-gaap")


class Submissions(BaseModel):
    cik: Union[str, int]
    entityType: Optional[str] = None
    sic: Optional[str] = None
    sicDescription: Optional[str] = None
    name: Optional[str] = None
    tickers: List[str]
    exchanges: List[str]
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


class SECFillings(BaseModel):
    companyfacts: CompanyFacts
    submissions: Submissions
