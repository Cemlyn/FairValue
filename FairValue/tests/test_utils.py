import pytest

from fairvalue.utils import (
    fill_dates,
    check_for_missing_dates,
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
