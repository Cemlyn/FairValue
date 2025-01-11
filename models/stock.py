from typing import List, Optional

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, model_validator

from models.base import Floats, Strs, NonNegFloats, NonNegInts
from utils import series_to_list
from constants import DATE_FORMAT


class TickerFinancials(BaseModel):
    operating_cashflows: Floats = Field(
        ..., description="Historic cashflows. Must be floats."
    )
    capital_expenditures: Floats = Field(
        ..., description="Historic capex. Must be floats."
    )
    year_end_dates: Strs = Field(
        ..., description="dates which each of the data points represent"
    )
    free_cashflows: Optional[Floats] = Field(
        None, description="Optional. Can be calculated from capex and cashflows"
    )
    shares_outstanding: NonNegInts = Field(description="Shares outstanding.")

    @model_validator(mode="before")
    def validate_lengths_and_calculate_fcf(cls, values):
        # Ensure all required fields have the same length
        required_fields = [
            "operating_cashflows",
            "capital_expenditures",
            "year_end_dates",
            "shares_outstanding",
        ]

        lengths = {
            field: len(values[field]) for field in required_fields if field in values
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        # Calculate free_cashflows if not provided
        if values.get("free_cashflows") is None:
            operating_cashflows = values["operating_cashflows"]
            capital_expenditures = values["capital_expenditures"]
            values["free_cashflows"] = Floats(
                data=[
                    ocf - capex
                    for ocf, capex in zip(operating_cashflows, capital_expenditures)
                ]
            )

        # Reindex for missing years
        dates = values.get("year_end_dates")
        dates = pd.Series(dates)
        dates = pd.to_datetime(dates)
        min_date = dates.min()
        max_date = dates.max()

        print("min date:", min_date)
        print("max date:", max_date)

        inferred_dates = []
        inferred_date = min_date - pd.Timedelta(days=365)
        while inferred_date + pd.Timedelta(days=365) < max_date:
            inferred_date = inferred_date + pd.Timedelta(days=365)
            inferred_dates.append(inferred_date)

        years = set([x.year for x in dates])
        print("years: ",years)
        inferred_years = set([x.year for x in inferred_dates])
        missing_years = inferred_years - years
        print("missing years: ", missing_years)

        if len(missing_years):

            mode_month = np.percentile([x.month for x in dates],40)
            mode_day = np.percentile([x.day for x in dates],40)

            missing_dates = pd.Series(pd.to_datetime([f"{year:.0f}-{mode_month:.0f}-{mode_day:.0f}" for year in missing_years]))

            #print("missing dates:",missing_dates)
            print("actual dates:", missing_dates)
            inferred_dates = pd.concat([missing_dates,
                                        pd.Series(dates)],axis=0).sort_values()

            df = pd.DataFrame({
                "operating_cashflows":values.get("operating_cashflows"),
                "capital_expenditures":values.get("capital_expenditures"),
                "year_end_dates":values.get("year_end_dates"),
                "shares_outstanding":values.get("shares_outstanding"),
                "free_cashflows":values.get("free_cashflows")
            })

            df = df.set_index("year_end_dates")
            df = df.reindex(inferred_dates).sort_index().reset_index()
            df["shares_outstanding"] = df["shares_outstanding"].ffill()
            df["shares_outstanding"] = df["shares_outstanding"].bfill()


            if df["shares_outstanding"].isna().mean():
                print("error!")

            values["operating_cashflows"] = Floats(data=series_to_list(df["operating_cashflows"].astype(float)))
            values["capital_expenditures"] = Floats(data=series_to_list(df["capital_expenditures"].astype(float)))
            values["shares_outstanding"] = NonNegInts(data=series_to_list(df["shares_outstanding"].astype(int)))
            values["year_end_dates"] = Strs(data=series_to_list(df["year_end_dates"].dt.strftime(DATE_FORMAT)))
            values["free_cashflows"] = Floats(data=series_to_list(df["free_cashflows"].astype(float)))

        return values


class ScenarioParams(BaseModel):
    """
    A Pydantic model to validate scenario parameters for financial analysis.
    """

    free_cashflows: Floats = Field(
        ..., description="Annual free cashflows. Must be floats."
    )
    discount_rates: NonNegFloats = Field(
        ..., description="Annual discount rates. Must be non-zero floats."
    )
    growth_rates: Floats = Field(
        ..., description="Annual growth rates."
    )
    terminal_growth_rate: float = Field(
        ..., description="Terminal growth rate. Must be a non-negative float."
    )

    shares_outstanding: NonNegInts = Field(..., description="all shares outstanding")

    @model_validator(mode="after")
    def validate_model(cls, values):
        """
        Validate the entire model to ensure consistency between fields.
        - free_cashflows and discount_rates must have the same length.
        - Discount rates must all be positive and non-zero.
        """
        # Check length consistency
        if not (len(values.free_cashflows) ==\
                 len(values.discount_rates) ==\
                    len(values.growth_rates) ==\
                        len(values.shares_outstanding)):
            raise ValueError(
                "The length of 'free_cashflows' and 'discount_rates' must be the same."
            )

        # Check discount rates are all positive and non-zero
        if any(rate <= 0 for rate in values.discount_rates):
            raise ValueError("All discount rates must be positive and non-zero.")

        return values
