import datetime
from typing import Optional, List

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    PositiveInt,
    confloat,
    conint,
)

from fairvalue.constants import (
    DATE_FORMAT,
)

from fairvalue._exceptions import FairValueException
from fairvalue.utils import date_to_datetime

NonNegFloat = confloat(ge=0)
NonNegInt = conint(ge=0)


class TickerFinancials(BaseModel):

    operating_cashflows: Optional[List[float]] = Field(
        None, description="Historic cashflows. Must be floats."
    )
    capital_expenditures: Optional[List[NonNegFloat]] = Field(
        None, description="Historic capex. Must be non-negative floats."
    )

    free_cashflows: Optional[List[float]] = Field(
        None,
        description="Optional. Can be calculated from capex and cashflows",
    )

    year_end_dates: List[str] = Field(
        ...,
        description="dates which each of the data points represent",
    )

    shares_outstanding: List[NonNegInt] = Field(description="Shares outstanding.")

    @model_validator(mode="before")
    def validate_data(cls, model):

        # check that captial expenditure and operating cashflows are provided if free_cashflow isn't
        if ("free_cashflows" not in model) and (
            ("operating_cashflows" not in model)
            or ("capital_expenditures" not in model)
        ):
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
            field: len(model[field]) for field in required_fields if field in model
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        parsed_dates = [
            datetime.datetime.strptime(date, DATE_FORMAT)
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

            free_cashflows = []
            for ops_cashflow, capex in zip(operating_cashflows, capital_expenditures):
                fcf = ops_cashflow - capex
                free_cashflows.append(fcf)

            model.free_cashflows = free_cashflows

        return model


class ForecastTickerFinancials(BaseModel):

    year_end_dates: List[str] = Field(
        ...,
        description="dates which each of the data points represent",
    )

    free_cashflows: List[float] = Field(
        None,
        description="freecashflows",
    )

    discount_rates: List[float] = Field(
        None,
        description="discount rate",
    )

    shares_outstanding: PositiveInt = Field(
        "Number of shares outstanding at the date the investor intends to sell."
    )

    terminal_growth: NonNegFloat = Field(
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
            field: len(model[field]) for field in required_fields if field in model
        }
        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"All fields must have the same length, but got lengths: {lengths}."
            )

        parsed_dates = [
            datetime.datetime.strptime(date, DATE_FORMAT)
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


def latest_index(date: datetime.datetime, year_end_dates: List[str]) -> int:
    """
    Determines the index corresponding to the first year-end date that is later than the provided date.

    Args:
        date (datetime): The reference date.
        year_end_dates (List[str]): A list of year-end dates as strings, formatted according to DATE_FORMAT.

    Raises:
        FairValueException: If the given date is earlier than the first year-end date.

    Returns:
        int: The index corresponding to the financial period for the given date.
    """

    if not isinstance(date, datetime.datetime):
        raise FairValueException("'datetime' must be a datetime object")

    if not year_end_dates:
        raise FairValueException("'year_end_dates' cannot be None")

    for n, x in enumerate(year_end_dates):

        year_end_date_obj = datetime.datetime.strptime(x, DATE_FORMAT)

        if date < year_end_date_obj:

            if n == 0:
                raise FairValueException(
                    f"Unable to retrieve financials before the date '{date}'"
                )
            return n

    return n + 1


def fetch_latest_financials(
    date: str, financials: TickerFinancials, shares_outstanding: int = None
):

    if financials is None:
        raise ValueError(
            "Unable to fetch latest historical financials. finanicals are 'None'"
        )
    elif len(financials.free_cashflows) == 0:
        raise FairValueException(
            "Unable to fetch financials. financials have len zero."
        )

    if date is None:
        raise ValueError(
            "date must be string of format '%Y-%m-%d', or datetime.date object"
        )

    if isinstance(date, str):
        date = datetime.datetime.strptime(date, DATE_FORMAT)
        date = date.replace(hour=23, minute=59, second=59)
    elif isinstance(date, datetime.date):
        date = date_to_datetime(date)
    elif not isinstance(date, datetime.date):
        raise ValueError(
            "'date' must be string of format '%Y-%m-%d', or datetime.date object"
        )

    n = latest_index(date, financials.year_end_dates)

    kwargs = {}
    kwargs["year_end_dates"] = financials.year_end_dates[:n]

    if shares_outstanding is None:
        kwargs["shares_outstanding"] = financials.shares_outstanding[:n]
    else:
        kwargs["shares_outstanding"] = [shares_outstanding] * (n)

    if financials.free_cashflows:
        kwargs["free_cashflows"] = financials.free_cashflows[:n]

    if financials.capital_expenditures:
        kwargs["capital_expenditures"] = financials.capital_expenditures[:n]

    if financials.operating_cashflows:
        kwargs["operating_cashflows"] = financials.operating_cashflows[:n]

    return TickerFinancials(**kwargs)
