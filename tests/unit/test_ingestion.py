import pandas as pd

from fairvalue._ingestion import datum_to_dataframe
from fairvalue.models.sec_ingestion import Datum


def test_datum_to_dataframe():

    data = [
        {
            "end": "2009-06-27",
            "val": 895816758,
            "accn": "0001193125-09-153165",
            "fy": 2009,
            "fp": "Q3",
            "form": "10-Q",
            "filed": "2009-07-22",
            "frame": "CY2009Q2I",
        },
        {
            "end": "2009-06-27",
            "val": 895816758,
            "accn": "0001193125-09-153165",
            "fy": 2009,
            "fp": "Q3",
            "form": "10-Q",
            "filed": "2009-07-22",
            "frame": "CY2009Q2I",
        },
        {
            "end": "2009-06-27",
            "val": 895816758,
            "accn": "0001193125-09-153165",
            "fy": 2009,
            "fp": "Q3",
            "form": "10-Q",
            "filed": "2009-07-22",
            "frame": "CY2009Q2I",
        },
    ]

    data = [Datum(**datum) for datum in data]
    result = datum_to_dataframe(data=data, col_name="capital_expenditure")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert len(result.columns) == 6
    assert "capital_expenditure" in result.columns
