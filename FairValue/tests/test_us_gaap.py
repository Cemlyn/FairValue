"""
Test fields required for intrinsic value calculation, that is:
- net cash from continuing operations
- capital expenditure (payments for property, plant and equipment)
"""

import pytest
from pydantic import ValidationError
from FairValue.models.ingestion import NetOpsCash, CapEx, USGaap


def test_net_ops_cash():

    data = {
        "label": "Net Cash Provided by (Used in) Operating Activities",
        "description": "Amount of cash inflow (outflow) from operating activities...",
        "units": {
            "USD": [
                {
                    "end": "2009-06-30",
                    "val": 2301,
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

    obj = NetOpsCash(**data)


def test_cap():

    data = {
        "label": "Payments to Acquire Property, Plant, and Equipment",
        "description": "Payments to Acquire Property, Plant, and Equipment...",
        "units": {
            "USD": [
                {
                    "end": "2009-01-10",
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

    obj = CapEx(**data)


def test_us_gaap():

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
