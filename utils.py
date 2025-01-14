import json
import statistics
from calendar import monthrange
from datetime import datetime

import pandas as pd

from constants import DATE_FORMAT


def series_to_list(series):
    return series.values.tolist()


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def datum_to_dataframe(data, col_name):
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


def fill_dates(dates: list) -> list:
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
    is_chronological = dates == sorted(dates)
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
