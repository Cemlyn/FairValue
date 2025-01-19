from typing import Optional
from datetime import datetime

import pandas as pd
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    ValidationError,
    PositiveInt,
)

from FairValue.models.base import Floats, Strs, NonNegInts
from FairValue.utils import fill_dates, series_to_list, check_for_missing_dates
from FairValue.constants import DATE_FORMAT


class TickerFinancials(BaseModel):
    operating_cashflows: Optional[Floats] = Field(
        None, description="Historic cashflows. Must be floats."
    )
    capital_expenditures: Optional[Floats] = Field(
        None, description="Historic capex. Must be floats."
    )
    year_end_dates: Strs = Field(
        ..., description="dates which each of the data points represent"
    )
    free_cashflows: Optional[Floats] = Field(
        None,
        description="Optional. Can be calculated from capex and cashflows",
    )
    shares_outstanding: NonNegInts = Field(description="Shares outstanding.")

    @model_validator(mode="before")
    def validate_data(cls, model):

        # check that captial expenditure and operating cashflows are provided if free_cashflow isn't
        if model["free_cashflows"] is None:
            if model["operating_cashflows"] is None:
                raise ValueError(
                    "If free_cashflows aren't provided operating_cashflows and capital_expenditures must be provided."
                )
            if model["operating_cashflows"] is None:
                raise ValueError(
                    "If free_cashflows aren't provided operating_cashflows and capital_expenditures must be provided."
                )

        # Ensure all required fields have the same length
        required_fields = [
            "operating_cashflows",
            "capital_expenditures",
            "year_end_dates",
            "shares_outstanding",
        ]

        lengths = {
            field: len(model[field])
            for field in required_fields
            if field in model
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        parsed_dates = [
            datetime.strptime(date, DATE_FORMAT)
            for date in model["year_end_dates"]
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
                    for ocf, capex in zip(
                        operating_cashflows, capital_expenditures
                    )
                ]
            )

        # Reindex for missing years
        missing_years = check_for_missing_dates(model.year_end_dates)

        if len(missing_years):

            filled_dates = fill_dates(model.year_end_dates)

            df = pd.DataFrame(
                {
                    "operating_cashflows": model.operating_cashflows,
                    "capital_expenditures": model.capital_expenditures,
                    "year_end_dates": model.year_end_dates,
                    "shares_outstanding": model.shares_outstanding,
                    "free_cashflows": model.free_cashflows,
                }
            )

            df = df.set_index("year_end_dates")
            df = df.reindex(filled_dates).sort_index().reset_index()

            df["shares_outstanding"] = df["shares_outstanding"].ffill()
            df["shares_outstanding"] = df["shares_outstanding"].bfill()

            if df["shares_outstanding"].isna().mean():
                raise ValidationError("shares outstanding contains nans.")

            model.operating_cashflows = Floats(
                data=series_to_list(df["operating_cashflows"].astype(float))
            )
            model.capital_expenditures = Floats(
                data=series_to_list(df["capital_expenditures"].astype(float))
            )
            model.shares_outstanding = NonNegInts(
                data=series_to_list(df["shares_outstanding"].astype(int))
            )
            model.year_end_dates = Strs(
                data=series_to_list(df["year_end_dates"])
            )
            model.free_cashflows = Floats(
                data=series_to_list(df["free_cashflows"].astype(float))
            )

        return model


class ForecastTickerFinancials(BaseModel):

    year_end_dates: Strs = Field(
        ..., description="Dates which each of the data points represent."
    )
    free_cashflows: Floats = Field(
        None, description="Annualised free cashflow. Must be floats."
    )
    discount_rates: Floats = Field(
        None, description="Annualised discount rate. Must be floats."
    )
    shares_outstanding: PositiveInt = Field(
        "Number of shares outstanding at the date the investor intends to sell."
    )
    terminal_growth: float = Field(
        description="Terminal Rate used in Gordon Growth Model for terminal growth rate."
    )

    @model_validator(mode="before")
    def validate_data(cls, model):
        # Ensure all required fields have the same length
        required_fields = [
            "year_end_dates",
            "free_cashflows",
            "discount_rates",
        ]

        lengths = {
            field: len(model[field])
            for field in required_fields
            if field in model
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        parsed_dates = [
            datetime.strptime(date, DATE_FORMAT)
            for date in model["year_end_dates"]
        ]
        years = [date.year for date in parsed_dates]

        if len(years) != len(set(years)):
            raise ValueError("duplicate dates found in 'end' column.")

        if model["terminal_growth"] >= model["discount_rates"][-1]:
            raise ValueError(
                "Terminal Growth rate must be lower than the final discount rate."
            )

        return model
