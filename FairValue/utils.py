import json
import statistics
from calendar import monthrange
from datetime import datetime, date, timedelta
from typing import List, Tuple
from dateutil.relativedelta import relativedelta

import pandas as pd

from FairValue.constants import DATE_FORMAT


def series_to_list(series):
    return series.values.tolist()


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def fill_dates(dates: List[str]) -> List[str]:
    """
    Takes a list of annual dates and check for missing years.
    E.g. [2019-01-01, 2021-01-01] -> [2019-01-01, 2020-01-01, 2021-01-01]

    Requires that the dates are already in chronological order.
    Inferred dates are set to the month end.
    """

    if not dates:
        raise ValueError("No dates provided.")

    # Convert date strings to datetime objects
    parsed_dates = [datetime.strptime(date, DATE_FORMAT) for date in dates]

    # Check if the list is sorted
    is_chronological = parsed_dates == sorted(parsed_dates)
    if not is_chronological:
        raise ValueError("Dates are not ordered chronologically.")

    # Generate all dates for the missing years
    mode_month = statistics.mode([d.month for d in parsed_dates])
    years_in_parsed_dates = [d.year for d in parsed_dates]

    start_year = parsed_dates[0].year
    end_year = parsed_dates[-1].year

    filled_dates = []
    count = 0
    for year in range(start_year, end_year + 1):

        # If year already exists take original date
        if year in years_in_parsed_dates:
            year_index = years_in_parsed_dates.index(year)
            filled_dates.append(parsed_dates[year_index].strftime(DATE_FORMAT))

        # Otherwise replace with an inferred date
        else:
            new_date = datetime(year, mode_month, 1)
            new_date = to_month_end(new_date).strftime(DATE_FORMAT)
            filled_dates.append(new_date)

        count += 1

    return filled_dates


def to_month_end(date):
    # Get the last day of the month
    last_day = monthrange(date.year, date.month)[1]
    # Return the datetime object for the month's end
    return datetime(date.year, date.month, last_day)


def generate_future_dates(n: int) -> List[str]:
    """
    Generate a list of year-end dates from today's date extending n years into the future.

    Args:
        n (int): Number of years into the future.

    Returns:
        list: A list of year-end dates as strings in the format "%Y-%m-%d".
    """
    if n < 0:
        raise ValueError("The number of years (n) must be non-negative.")

    today = date.today()

    future_dates = [
        (today + timedelta(days=365 * i)).strftime(DATE_FORMAT)
        for i in range(n)
    ]
    return future_dates


def check_for_missing_dates(date_strings: List[str]) -> List[int]:

    # Convert strings to datetime objects
    dates = [datetime.strptime(date, DATE_FORMAT) for date in date_strings]

    # Find the minimum and maximum dates
    min_date = min(dates)
    max_date = max(dates)

    # Generate a list of dates spanning from min_date to max_date with yearly intervals
    dts = [min_date]
    while dts[-1] < max_date:
        dts.append(
            dts[-1] + relativedelta(years=1)
        )  # Approximation for a year

    # Extract years from the original dates and the generated date range
    years = {date.year for date in dates}
    dts_years = {date.year for date in dts}

    # Find the missing years
    missing_years = dts_years - years

    return list(missing_years)


class RoundedDict:
    def __init__(self, input_dict=None):
        """Initialize the wrapper with an optional dictionary."""
        self._dict = {}
        if input_dict:
            self.update(input_dict)

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = self._round_if_float(value)

    def __delitem__(self, key):
        del self._dict[key]

    def __repr__(self):
        return repr(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def update(self, other):
        for key, value in other.items():
            self[key] = value

    def _round_if_float(self, value):
        """Round the value to two decimal places if it's a float."""
        if isinstance(value, float):
            return round(value, 2)
        return value


def drop_nans(
    a: List[float], b: List[float]
) -> Tuple[List[float], List[float]]:
    """
    Removes NaN values from list `b` and their corresponding values in list `a`.

    Args:
        a (List[float]): The first list of values.
        b (List[float]): The second list of values, potentially containing NaNs.

    Returns:
        Tuple[List[float], List[float]]: Two lists with NaNs removed from `b` and corresponding indices from `a`.
    """
    if len(a) != len(b):
        raise ValueError("The lengths of 'a' and 'b' must be equal.")

    filtered_a = []
    filtered_b = []

    for value_a, value_b in zip(a, b):
        if not pd.isnull(value_b):
            filtered_a.append(value_a)
            filtered_b.append(value_b)

    return filtered_a, filtered_b
