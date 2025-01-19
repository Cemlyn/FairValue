import pytest
from pydantic import ValidationError
from models.ingestion import Shares, Datum


def test_dei_datum_valid():
    data = {
        "end": "2023-12-31",
        "val": 1000,
        "accn": "0001234567-23-000001",
        "fy": 2023,
        "fp": "Q4",
        "form": "10-Q",
        "filed": "2024-01-15",
        "frame": "CY2023Q4I",
    }
    obj = Datum(**data)
    assert obj.end == "2023-12-31"
    assert obj.filed == "2024-01-15"


def test_dei_datum_invalid_end():
    data = {
        "end": "invalid-date",
        "val": 1000,
        "accn": "0001234567-23-000001",
        "fy": 2023,
        "fp": "Q4",
        "form": "10-Q",
        "filed": "2024-01-15",
        "frame": "CY2023Q4I",
    }
    with pytest.raises(
        ValidationError,
        match="Invalid Date field. 'end' must be of the format 'YYYY-MM-DD'.",
    ):
        Datum(**data)


def test_dei_datum_invalid_filed():
    data = {
        "end": "2023-12-31",
        "val": 1000,
        "accn": "0001234567-23-000001",
        "fy": 2023,
        "fp": "Q4",
        "form": "10-Q",
        "filed": "invalid-date",
        "frame": "CY2023Q4I",
    }
    with pytest.raises(
        ValidationError,
        match="Invalid Date field. 'filed' must be of the format 'YYYY-MM-DD'.",
    ):
        Datum(**data)


def test_shares_valid():
    data = {
        "shares": [
            {
                "end": "2023-12-31",
                "val": 1000,
                "accn": "0001234567-23-000001",
                "fy": 2023,
                "fp": "Q4",
                "form": "10-Q",
                "filed": "2023-12-31",
                "frame": "CY2023Q4I",
            }
        ]
    }
    obj = Shares(**data)
