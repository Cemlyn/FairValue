from typing import Optional
from datetime import datetime

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, model_validator, ValidationError

from models.base import Floats, Strs, NonNegFloats, NonNegInts
from utils import fill_dates
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
    def validate_lengths(cls, model):
        # Ensure all required fields have the same length
        required_fields = [
            "operating_cashflows",
            "capital_expenditures",
            "year_end_dates",
            "shares_outstanding",
        ]

        lengths = {
            field: len(model[field]) for field in required_fields if field in model
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        parsed_dates = [
            datetime.strptime(date, DATE_FORMAT) for date in model["year_end_dates"]
        ]
        years = [date.year for date in parsed_dates]

        if len(years) != len(set(years)):
            raise ValueError("duplicate dates found in 'end' column.")

        return model

    @model_validator(mode="after")
    def postprocessing(cls, model):

        # Calculate free_cashflows if not provided
        if model.free_cashflows is None:
            operating_cashflows = model.operating_cashflows
            capital_expenditures = model.capital_expenditures
            model.free_cashflows = Floats(
                data=[
                    ocf - capex
                    for ocf, capex in zip(operating_cashflows, capital_expenditures)
                ]
            )

        # Reindex for missing years
        dates = pd.Series(model.year_end_dates)
        dates = pd.to_datetime(dates, format=DATE_FORMAT)
        min_date = dates.min()
        max_date = dates.max()

        dts = [min_date]
        while dts[-1] < max_date:
            dts.append(dts[-1] + pd.Timedelta(days=365))

        years = set([x.year for x in dates])
        dts_years = set([x.year for x in dts])
        missing_years = dts_years - years

        if len(missing_years):

            filled_dates = fill_dates([x.strftime(DATE_FORMAT) for x in dates])

            df = pd.DataFrame(
                {
                    "operating_cashflows": model.operating_cashflows,
                    "capital_expenditures": model.capital_expenditures,
                    "year_end_dates": model.year_end_dates,
                    "shares_outstanding": model.shares_outstanding,
                    "free_cashflows": model.free_cashflows,
                }
            )

            try:
                df = df.set_index("year_end_dates")
                df = df.reindex(filled_dates).sort_index().reset_index()
            except:
                import sys

                df.to_csv("failed.csv")
                sys.exit(0)
            df["shares_outstanding"] = df["shares_outstanding"].ffill()
            df["shares_outstanding"] = df["shares_outstanding"].bfill()

            # if df["shares_outstanding"].isna().mean():
            #     raise ValidationError("shares outstanding contains nans.")

        #     model["operating_cashflows"] = Floats(data=series_to_list(df["operating_cashflows"].astype(float)))
        #     model["capital_expenditures"] = Floats(data=series_to_list(df["capital_expenditures"].astype(float)))
        #     model["shares_outstanding"] = NonNegInts(data=series_to_list(df["shares_outstanding"].astype(int)))
        #     model["year_end_dates"] = Strs(data=series_to_list(df["year_end_dates"].dt.strftime(DATE_FORMAT)))
        #     model["free_cashflows"] = Floats(data=series_to_list(df["free_cashflows"].astype(float)))

        return model


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
    growth_rates: Floats = Field(..., description="Annual growth rates.")
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
        if not (
            len(values.free_cashflows)
            == len(values.discount_rates)
            == len(values.growth_rates)
            == len(values.shares_outstanding)
        ):
            raise ValueError(
                "The length of 'free_cashflows' and 'discount_rates' must be the same."
            )

        # Check discount rates are all positive and non-zero
        if any(rate <= 0 for rate in values.discount_rates):
            raise ValueError("All discount rates must be positive and non-zero.")

        return values
