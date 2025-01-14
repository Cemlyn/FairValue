import pytest

from utils import fill_dates


def test_valid_sequence():

    dates = ["2018-01-01", "2019-02-28", "2020-02-29"]
    filled_dates = fill_dates(dates)
    assert dates == filled_dates

    dates = ["2018-01-01", "2020-02-29"]
    filled_dates = fill_dates(dates)
    assert filled_dates == ["2018-01-01", "2019-01-31", "2020-02-29"]


def test_invalid_inputs():

    with pytest.raises(ValueError) as exc_info:
        fill_dates(["2019-02-28", "2018-01-01", "2020-02-29"])

    # Inspect the exception
    assert str(exc_info.value) == "Dates are not ordered chronologically."
