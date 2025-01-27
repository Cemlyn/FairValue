import copy
from datetime import datetime
from typing import List, Optional, Union, Literal, Dict

from pydantic import BaseModel, Field, field_validator
from fairvalue.models.utils import validate_date
from fairvalue.constants import DATE_FORMAT


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
    val: int
    accn: Optional[str] = None
    fy: Optional[int] = None
    fp: Optional[str] = None
    form: Literal["10-K", "20-F", "6-K", "20-F/A", "10-Q", "10-Q/A", "10-K/A"]
    filed: str  # Must be a valid date
    frame: Optional[str] = None

    @field_validator("end", "filed", mode="before")
    def validate_end(cls, value):
        return validate_date("end", value)


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


class Dei(BaseModel):

    EntityCommonStockSharesOutstanding: FinancialMetric
    EntityPublicFloat: Optional[FinancialMetric] = None
    EntityListingDepositoryReceiptRatio: Optional[FinancialMetric] = None

    model_config = {"extra": "allow"}


class Facts(BaseModel):

    dei: Dei
    us_gaap: USGaap = Field(alias="us-gaap")


class ParseException(Exception):
    pass


class CompanyFacts(BaseModel):

    cik: Union[str, int]
    entityName: str
    facts: Facts

    # awd
    operating_cashflow: Union[FinancialMetric, None] = Field(default=None, exclude=True)
    capital_expenditure: Union[FinancialMetric, None] = Field(
        default=None, exclude=True
    )
    shares_outstanding: Union[FinancialMetric, None] = Field(default=None, exclude=True)
    shares_outstanding_aligned: Union[FinancialMetric, None] = Field(
        default=None, exclude=True
    )

    latest_shares_outstanding: Union[int,None] = Field(default=None, exclude=None)

    def __post_init_post_parse__(self):
        """
        This section:
        0. Removes leading zeros from the cik
        1. Tries to populate the operating_cashflow and capital_expenditures attributes.
        2. For foreign stocks like BABA it will try to apply conversions from the CNY to USD equivalent:
            2.0: convert shares_outstanding to their NYSE or NASDAQ equivalent volume.
            2.1: ensure that financials in the foreign currency are provided not the holding companies.
        3. Brings the shares outstanding inline with captial_expenditure and operating cashflows w.r.t dates.
        """

        self.cik = str(self.cik).lstrip("0")

        is_foreign = False

        currencies = list(
            self.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units.keys()
        )
        count_currencies = len(currencies)

        capital_expenditure = None
        if count_currencies == 0:
            raise ParseException("Unable to parse filing. Missing currency data.")

        elif count_currencies == 1:
            if "USD" not in currencies:
                raise ParseException("Unable to parse filing. Missing currency data.")
            operating_cashflow = (
                self.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
                    "USD"
                ]
            )
            if hasattr(
                self.facts.us_gaap, "PaymentsToAcquirePropertyPlantAndEquipment"
            ) and hasattr(
                self.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment, "units"
            ):
                capital_expenditure = (
                    self.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
                        "USD"
                    ]
                )

        elif count_currencies == 2:
            if "USD" not in currencies:
                raise ParseException(
                    "Unable to parse filing. Mutliple non-USD currencies found."
                )

            is_foreign = True
            currencies = [curr for curr in currencies if curr != "USD"]
            (currency,) = currencies
            operating_cashflow = (
                self.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
                    currency
                ]
            )
            if self.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment:
                capital_expenditure = (
                    self.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
                        currency
                    ]
                )

        else:
            raise ParseException(
                "Unable to parse filing. Mutliple non-USD currencies found."
            )

        self.operating_cashflow = operating_cashflow
        self.capital_expenditure = capital_expenditure

        shares_outstanding = self.facts.dei.EntityCommonStockSharesOutstanding.units[
            "shares"
        ]

        # Converting shares outstanding into their USD equivalent
        if is_foreign:

            if hasattr(
                self.facts.dei, "EntityListingDepositoryReceiptRatio"
            ) and hasattr(self.facts.dei.EntityListingDepositoryReceiptRatio, "units"):
                adr_ratios = self.facts.dei.EntityListingDepositoryReceiptRatio.units[
                    "pure"
                ]
            else:
                raise ParseException(
                    "Could not find EntityListingDepositoryReceiptRatio in filing."
                )

            shares_outstanding_adj = []
            for share_count in shares_outstanding:

                share_count_date = datetime.strptime(share_count.end, DATE_FORMAT)

                for n, adr_ratio in enumerate(adr_ratios):

                    adr_ratio_date = datetime.strptime(adr_ratio.end, DATE_FORMAT)
                    if adr_ratio_date > share_count_date:
                        break

                share_count_copy = copy.deepcopy(share_count)
                share_count_adj = share_count_copy.val / adr_ratios[n - 1].val
                share_count_copy.val = share_count_adj

                shares_outstanding_adj.append(share_count_copy)

            self.shares_outstanding = shares_outstanding

        else:
            self.shares_outstanding = shares_outstanding

        self.latest_shares_outstanding = self.shares_outstanding[-1].val

        # Bringing shares outstanding inline with capex and cashflows
        shares_outstanding_aligned = []
        for op_cashflow in self.operating_cashflow:

            op_cashflow_date = datetime.strptime(op_cashflow.end, DATE_FORMAT)

            for n, share_count in enumerate(self.shares_outstanding):

                op_cf_date = datetime.strptime(share_count.end, DATE_FORMAT)
                if op_cf_date > op_cashflow_date:
                    break

            op_cashflow_copy = copy.deepcopy(op_cashflow)
            op_cashflow_copy.val = self.shares_outstanding[n - 1].val

            shares_outstanding_aligned.append(op_cashflow_copy)

        self.shares_outstanding_aligned = shares_outstanding_aligned
