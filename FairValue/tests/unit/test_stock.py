import pytest
import datetime

from fairvalue._stock import latest_index, FairValueException


@pytest.mark.parametrize(
    ("inputs", "expected_output"),
    [
        (
            (
                datetime.datetime(2018, 1, 1, 0, 0, 0),
                ["2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01"],
            ),
            1,
        ),
        (
            (
                datetime.datetime(2019, 1, 1, 0, 0, 0),
                ["2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01"],
            ),
            2,
        ),
        (
            (
                datetime.datetime(2022, 1, 1, 0, 0, 0),
                ["2018-02-01", "2019-01-01", "2020-01-01", "2021-01-01"],
            ),
            4,
        ),
    ],
)
def test_latest_index(inputs, expected_output):
    output = latest_index(*inputs)
    assert output == expected_output


def test_error():
    date = datetime.datetime(2017, 1, 1, 0, 0, 0)
    dates = ["2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01"]
    with pytest.raises(
        FairValueException,
    ):
        latest_index(date, dates)
