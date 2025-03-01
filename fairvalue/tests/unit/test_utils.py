import pytest
import datetime

from fairvalue.utils import (
    fill_dates,
    check_for_missing_dates,
    generate_future_dates,
    DATE_FORMAT,
)


def test_valid_sequence():

    dates = [
        "2018-01-01",
        "2019-02-28",
        "2020-02-29",
    ]
    filled_dates = fill_dates(dates)
    assert dates == filled_dates

    dates = [
        "2018-01-01",
        "2020-02-29",
    ]
    filled_dates = fill_dates(dates)
    assert filled_dates == [
        "2018-01-01",
        "2019-01-31",
        "2020-02-29",
    ]


def test_invalid_inputs():

    with pytest.raises(ValueError) as exc_info:
        fill_dates(
            [
                "2019-02-28",
                "2018-01-01",
                "2020-02-29",
            ]
        )

    # Inspect the exception
    assert str(exc_info.value) == "Dates are not ordered chronologically."


def test_for_leap_years():

    # leap year example without missing data
    dates = [
        "2009-05-31",
        "2010-05-31",
        "2011-05-31",
        "2012-05-31",
        "2012-05-31",
    ]
    missing_dates = check_for_missing_dates(dates)
    assert missing_dates != [2013]
    assert len(missing_dates) == 0

    # leap year example with missing data
    dates = [
        "2009-05-31",
        "2011-05-31",
        "2012-05-31",
        "2012-05-31",
    ]
    missing_dates = check_for_missing_dates(dates)
    assert missing_dates == [2010]
    assert len(missing_dates) == 1

    # leap year example with missing data
    dates = [
        "2009-05-31",
        "2012-05-31",
    ]
    missing_dates = check_for_missing_dates(dates)
    assert missing_dates == [
        2010,
        2011,
    ]
    assert len(missing_dates) == 2

    # leap year example with missing data
    dates = ["2018-01-01", "2020-02-01", "2021-02-01", "2022-02-01"]
    missing_dates = check_for_missing_dates(dates)
    assert missing_dates == [
        2019,
    ]
    assert len(missing_dates) == 1


def test_generate_future_dates():
    # Generate 800 test dates starting from 2023-01-01 through to 2025. Note that 2024 is a leap year.
    all_dates = [
        datetime.date(2023, 1, 1) + datetime.timedelta(days=i) for i in range(800)
    ]

    for forecast_date in all_dates:
        generated_dates = generate_future_dates(forecast_date, 10)
        generated_years = [
            datetime.datetime.strptime(d, DATE_FORMAT).year for d in generated_dates
        ]

        # Ensure all generated years are unique
        assert len(set(generated_years)) == len(
            generated_years
        ), f"Duplicate years for start date {forecast_date}"
