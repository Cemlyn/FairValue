"""
Test fields required for intrinsic value calculation, that is:
- net cash from continuing operations
- capital expenditure (payments for property, plant and equipment)
"""

import pytest
from pydantic import (
    ValidationError,
)
from fairvalue.models.ingestion import (
    Dei,
)


@pytest.mark.parametrize(
    "data",
    [
        # Test case with only shares
        {
            "EntityCommonStockSharesOutstanding": {
                "label": "Entity Common Stock, Shares Outstanding",
                "description": "Indicate number of shares or other units outstanding of each of registrant's classes of capital or common stock or other ownership interests, if and as stated on cover of related periodic report. Where multiple classes or units exist define each class/interest by adding class of stock items such as Common Class A [Member], Common Class B [Member] or Partnership Interest [Member] onto the Instrument [Domain] of the Entity Listings, Instrument.",
                "units": {
                    "shares": [
                        {
                            "end": "2009-06-27",
                            "val": 895816758,
                            "accn": "0001193125-09-153165",
                            "fy": 2009,
                            "fp": "Q3",
                            "form": "10-Q",
                            "filed": "2009-07-22",
                            "frame": "CY2009Q2I",
                        }
                    ]
                },
            }
        }
    ],
)
def test_dei_no_validation_error(data):
    """Test that Dei model does not raise a Pydantic ValidationError."""
    try:
        Dei(**data)
    except ValidationError as e:
        pytest.fail(f"Unexpected Pydantic ValidationError raised: {e}")


@pytest.mark.parametrize(
    "data",
    [
        # Test case with only shares
        {
            "EntityCommonStockSharesOutstanding": {
                "label": "Entity Common Stock, Shares Outstanding",
                "description": "Indicate number of shares or other units outstanding of each of registrant's classes of capital or common stock or other ownership interests, if and as stated on cover of related periodic report. Where multiple classes or units exist define each class/interest by adding class of stock items such as Common Class A [Member], Common Class B [Member] or Partnership Interest [Member] onto the Instrument [Domain] of the Entity Listings, Instrument.",
                "units": {
                    "shares": [
                        {
                            "end": "2009-06-27",
                            "val": -123,
                            "accn": "0001193125-09-153165",
                            "fy": 2009,
                            "fp": "Q3",
                            "form": "10-Q",
                            "filed": "2009-07-22",
                            "frame": "CY2009Q2I",
                        }
                    ]
                },
            }
        },
        {
            "EntityCommonStockSharesOutstanding": {
                "label": "Entity Common Stock, Shares Outstanding",
                "description": "Indicate number of shares or other units outstanding of each of registrant's classes of capital or common stock or other ownership interests, if and as stated on cover of related periodic report. Where multiple classes or units exist define each class/interest by adding class of stock items such as Common Class A [Member], Common Class B [Member] or Partnership Interest [Member] onto the Instrument [Domain] of the Entity Listings, Instrument.",
                "units": {
                    "shares": [
                        {
                            "end": "2009-06-27",
                            "val": None,
                            "accn": "0001193125-09-153165",
                            "fy": 2009,
                            "fp": "Q3",
                            "form": "10-Q",
                            "filed": "2009-07-22",
                            "frame": "CY2009Q2I",
                        }
                    ]
                },
            }
        },
    ],
)
def test_dei_validation_error(data):

    with pytest.raises(
        ValidationError,
    ):
        obj = Dei(**data)


@pytest.mark.parametrize(
    "data",
    [
        # Test case with only shares
        {
            "EntityCommonStockSharesOutstanding": {
                "label": "Entity Common Stock, Shares Outstanding",
                "description": "Indicate number of shares or other units outstanding of each of registrant's classes of capital or common stock or other ownership interests, if and as stated on cover of related periodic report. Where multiple classes or units exist define each class/interest by adding class of stock items such as Common Class A [Member], Common Class B [Member] or Partnership Interest [Member] onto the Instrument [Domain] of the Entity Listings, Instrument.",
                "units": {
                    "shares": [
                        {
                            "end": "2009-06-27",
                            "val": 895816758.0,
                            "accn": "0001193125-09-153165",
                            "fy": 2009,
                            "fp": "Q3",
                            "form": "10-Q",
                            "filed": "2009-07-22",
                            "frame": "CY2009Q2I",
                        }
                    ]
                },
            }
        }
    ],
)
def test_dei_shares_outstanding_conversion(data):
    """Test that Dei model doesn't return shares outstanding that are floats"""
    obj = Dei(**data)
    shares_outstanding = obj.EntityCommonStockSharesOutstanding.units["shares"][0].val
    assert isinstance(shares_outstanding, int)
    assert shares_outstanding == 895816758
