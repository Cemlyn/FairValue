"""
Test fields required for intrinsic value calculation, that is:
- net cash from continuing operations
- capital expenditure (payments for property, plant and equipment)
"""

import pytest
from pydantic import (
    ValidationError,
)
from fairvalue.models.sec_ingestion import (
    USGaap,
)


@pytest.mark.parametrize(
    "data",
    [
        # First test case (with both fields)
        {
            "NetCashProvidedByUsedInOperatingActivities": {
                "label": "Net Cash Provided by (Used in) Operating Activities",
                "description": "Amount of cash inflow (outflow) from operating activities, including discontinued operations...",
                "units": {
                    "USD": [
                        {
                            "start": "2008-01-01",
                            "end": "2008-06-30",
                            "val": 3063626000,
                            "accn": "0001104659-09-048013",
                            "fy": 2009,
                            "fp": "Q2",
                            "form": "10-Q",
                            "filed": "2009-08-07",
                            "frame": "CY2007",
                        }
                    ]
                },
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "label": "Payments to Acquire Property, Plant, and Equipment",
                "description": "The cash outflow associated with the acquisition of long-lived...",
                "units": {
                    "USD": [
                        {
                            "start": "2007-01-01",
                            "end": "2007-12-31",
                            "val": 1656207000,
                            "accn": "0001047469-10-001018",
                            "fy": 2009,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2010-02-19",
                            "frame": "CY2007",
                        }
                    ]
                },
            },
            "CommonStockSharesOutstanding": {
                "label": "Common Stock, Shares, Outstanding",
                "description": "Number of shares of common stock outstanding. Common stock represent the ownership interest in a corporation.",
                "units": {
                    "shares": [
                        {
                            "start": "2007-01-01",
                            "end": "2007-12-31",
                            "val": 1656207000,
                            "accn": "0001047469-10-001018",
                            "fy": 2009,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2010-02-19",
                            "frame": "CY2007",
                        }
                    ]
                },
            },
        },
        # Second test case (with only one field)
        {
            "NetCashProvidedByUsedInOperatingActivities": {
                "label": "Net Cash Provided by (Used in) Operating Activities",
                "description": "Amount of cash inflow (outflow) from operating activities, including discontinued operations...",
                "units": {
                    "USD": [
                        {
                            "start": "2008-01-01",
                            "end": "2008-06-30",
                            "val": 3063626000,
                            "accn": "0001104659-09-048013",
                            "fy": 2009,
                            "fp": "Q2",
                            "form": "10-Q",
                            "filed": "2009-08-07",
                            "frame": "CY2007",
                        }
                    ]
                },
            },
            "CommonStockSharesOutstanding": {
                "label": "Common Stock, Shares, Outstanding",
                "description": "Number of shares of common stock outstanding. Common stock represent the ownership interest in a corporation.",
                "units": {
                    "shares": [
                        {
                            "start": "2007-01-01",
                            "end": "2007-12-31",
                            "val": 1656207000,
                            "accn": "0001047469-10-001018",
                            "fy": 2009,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2010-02-19",
                            "frame": "CY2007",
                        }
                    ]
                },
            },
        },
    ],
)
def test_us_gaap_no_validation_error(data):
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    try:
        obj = USGaap(**data)
    except ValidationError as e:
        pytest.fail(f"Unexpected Pydantic ValidationError raised: {e}")


def test_us_gaap_conversion():

    data = {
        "NetCashProvidedByUsedInOperatingActivities": {
            "label": "Net Cash Provided by (Used in) Operating Activities",
            "description": "Amount of cash inflow (outflow) from operating activities, including discontinued operations...",
            "units": {
                "USD": [
                    {
                        "start": "2008-01-01",
                        "end": "2008-06-30",
                        "val": 3063626000,
                        "accn": "0001104659-09-048013",
                        "fy": 2009,
                        "fp": "Q2",
                        "form": "10-Q",
                        "filed": "2009-08-07",
                        "frame": "CY2007",
                    }
                ]
            },
        },
        "CommonStockSharesOutstanding": {
            "label": "Common Stock, Shares, Outstanding",
            "description": "Number of shares of common stock outstanding. Common stock represent the ownership interest in a corporation.",
            "units": {
                "shares": [
                    {
                        "start": "2007-01-01",
                        "end": "2007-12-31",
                        "val": 1656207000,
                        "accn": "0001047469-10-001018",
                        "fy": 2009,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2010-02-19",
                        "frame": "CY2007",
                    }
                ]
            },
        },
        "PaymentsToAcquirePropertyPlantAndEquipment": {
            "label": "Payments to Acquire Property, Plant, and Equipment",
            "description": "The cash outflow associated with the acquisition of long-lived...",
            "units": {
                "USD": [
                    {
                        "start": "2007-01-01",
                        "end": "2007-12-31",
                        "val": 1656207000,
                        "accn": "0001047469-10-001018",
                        "fy": 2009,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2010-02-19",
                        "frame": "CY2007",
                    }
                ]
            },
        },
    }

    obj = USGaap(**data)

    val = obj.PaymentsToAcquirePropertyPlantAndEquipment.units["USD"][0].val
    assert isinstance(val, float)

    val = obj.NetCashProvidedByUsedInOperatingActivities.units["USD"][0].val
    assert isinstance(val, float)


def test_missing_field():

    data = {
        "PaymentsToAcquirePropertyPlantAndEquipment": {
            "label": "Payments to Acquire Property, Plant, and Equipment",
            "description": "The cash outflow associated with the acquisition of long-lived...",
            "units": {
                "USD": [
                    {
                        "start": "2007-01-01",
                        "end": "2007-12-31",
                        "val": 1656207000,
                        "accn": "0001047469-10-001018",
                        "fy": 2009,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2010-02-19",
                        "frame": "CY2007",
                    }
                ]
            },
        },
    }

    with pytest.raises(
        ValidationError,
    ):
        obj = USGaap(**data)
