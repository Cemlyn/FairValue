"""
Test fields required for intrinsic value calculation, that is:
- common stock shares outstanding
"""

import pytest
from pydantic import ValidationError
from models.ingestion import CommonStockSharesOutstanding


def test_common_stock_shares_outstanding():

    data = {
        "label": "Entity Common Stock, Shares Outstanding",
        "description": "Indicate number of shares or other units outstanding of each of...",
        "units": {
            "shares": [
                {
                    "end": "2009-06-30",
                    "val": 1545912443,
                    "accn": "0001104659-09-048013",
                    "fy": 2009,
                    "fp": "Q2",
                    "form": "10-Q",
                    "filed": "2009-08-07",
                    "frame": "CY2009Q2I",
                }
            ]
        },
    }

    obj = CommonStockSharesOutstanding(**data)


def test_common_stock_shares_outstanding_invalid():

    data = {
        "label": "Entity Common Stock, Shares Outstanding",
        "description": "Indicate number of shares or other units outstanding of each of...",
        "units": {
            "shares": [
                {
                    "end": "2009-hello",
                    "val": 1545912443,
                    "accn": "0001104659-09-048013",
                    "fy": 2009,
                    "fp": "Q2",
                    "form": "10-Q",
                    "filed": "2009-08-07",
                    "frame": "CY2009Q2I",
                }
            ]
        },
    }

    with pytest.raises(
        ValidationError,
        match="Invalid Date field. 'end' must be of the format 'YYYY-MM-DD'.",
    ):
        CommonStockSharesOutstanding(**data)

    data = {
        "label": "Entity Common Stock, Shares Outstanding",
        "description": "Indicate number of shares or other units outstanding of each of...",
        "units": {
            "shares": [
                {
                    "end": "2009-01-01",
                    "val": 1545912443,
                    "accn": "0001104659-09-048013",
                    "fy": 2009,
                    "fp": "Q2",
                    "form": "10-Q",
                    "filed": "2009-bye-bye",
                    "frame": "CY2009Q2I",
                }
            ]
        },
    }

    with pytest.raises(
        ValidationError,
        match="Invalid Date field. 'filed' must be of the format 'YYYY-MM-DD'.",
    ):
        CommonStockSharesOutstanding(**data)

    data = {
        "label": "Entity Common Stock, Shares Outstanding",
        "description": "Indicate number of shares or other units outstanding of each of...",
        "units": {
            "shares": [
                {
                    "val": 1545912443,
                    "accn": "0001104659-09-048013",
                    "fy": 2009,
                    "fp": "Q2",
                    "form": "10-Q",
                    "filed": "2009-10-01",
                    "frame": "CY2009Q2I",
                }
            ]
        },
    }

    with pytest.raises(ValidationError):
        CommonStockSharesOutstanding(**data)


def test_dei():
    pass
