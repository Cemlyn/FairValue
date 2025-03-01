import json
import statistics
import calendar
import datetime
from typing import List, Tuple

import pandas as pd

from fairvalue.constants import DATE_FORMAT


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
    parsed_dates = [datetime.datetime.strptime(date, DATE_FORMAT) for date in dates]

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
    for year in range(start_year, end_year + 1):

        # If year already exists take original date
        if year in years_in_parsed_dates:
            year_index = years_in_parsed_dates.index(year)
            filled_dates.append(parsed_dates[year_index].strftime(DATE_FORMAT))

        # Otherwise replace with an inferred date
        else:
            new_date = datetime.datetime(year, mode_month, 1)
            new_date = to_month_end(new_date).strftime(DATE_FORMAT)
            filled_dates.append(new_date)

    return filled_dates


def to_month_end(date):
    # Get the last day of the month
    last_day = calendar.monthrange(date.year, date.month)[1]
    # Return the datetime object for the month's end
    return datetime.datetime(date.year, date.month, last_day)


def generate_future_dates(date: datetime.date, n: int) -> List[str]:
    future_dates = []

    for i in range(1, n + 1):
        new_year = date.year + i

        # Handle February 29 separately
        if date.month == 2 and date.day == 29 and not calendar.isleap(new_year):
            future_dates.append(datetime.date(new_year, 2, 28).strftime("%Y-%m-%d"))
        else:
            future_dates.append(
                datetime.date(new_year, date.month, date.day).strftime("%Y-%m-%d")
            )

    return future_dates


def check_for_missing_dates(date_strings: List[str]) -> List[int]:

    if not date_strings:
        return []  # Return an empty list if there are no dates

    DATE_FORMAT = "%Y-%m-%d"  # Ensure date format is defined
    dates = [datetime.datetime.strptime(date, DATE_FORMAT) for date in date_strings]

    min_year = min(dates).year
    max_year = max(dates).year

    # Generate full range of years
    all_years = set(range(min_year, max_year + 1))
    present_years = {date.year for date in dates}

    # Find missing years
    missing_years = sorted(all_years - present_years)

    return missing_years


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


def drop_nans(a: List[float], b: List[float]) -> Tuple[List[float], List[float]]:
    """
    Removes NaN values from list `b` and their corresponding values in list `a`.

    Args:
        a (List[float]): The first list of values.
        b (List[float]): The second list of values, potentially containing NaNs.

    Returns:
        Tuple[List[float], List[float]]: lists with NaNs removed.
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


def date_to_datetime(date: datetime.date):

    if not isinstance(date, datetime.date):
        raise ValueError("'date' must be a datetime.date object")

    return datetime.datetime.combine(date, datetime.time(23, 59, 59, 999999))
