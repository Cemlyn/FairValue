import os
import pytest

import pandas as pd

from fairvalue.utils import load_json
from fairvalue.models.ingestion import SECFilings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_PATH = os.path.join(BASE_DIR, "..", "..", "data", "APPL")


@pytest.fixture
def company_facts_dict():
    return load_json(
        os.path.join(TEST_DATA_PATH, "sec-filing-companyfacts-CIK0000320193.json")
    )


@pytest.fixture
def submissions_dict():
    return load_json(
        os.path.join(TEST_DATA_PATH, "sec-filing-submissions-CIK0000320193.json")
    )


@pytest.fixture
def capital_expenditures_recon():
    return pd.read_csv(
        os.path.join(TEST_DATA_PATH, "reconciliation-capital-expenditures.csv")
    )


def test_financials_capital_expenditures(
    company_facts_dict, submissions_dict, capital_expenditures_recon
):

    sec_filling = SECFilings(
        companyfacts=company_facts_dict, submissions=submissions_dict
    )

    capex_values = (
        sec_filling.companyfacts.facts.us_gaap.CommonStockSharesOutstanding.units[
            "shares"
        ]
    )

    capex_values == capital_expenditures_recon.values.ravel().tolist()


@pytest.fixture
def net_ops_cashflows_recon():
    return pd.read_csv(
        os.path.join(TEST_DATA_PATH, "reconciliation-net-ops-cashflows.csv")
    )


def test_financials_net_ops_cashflows(
    company_facts_dict, submissions_dict, net_ops_cashflows_recon
):

    sec_filling = SECFilings(
        companyfacts=company_facts_dict, submissions=submissions_dict
    )

    capex_values = sec_filling.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
        "USD"
    ]

    capex_values == net_ops_cashflows_recon.values.ravel().tolist()


@pytest.fixture
def shares_outstanding_recon():
    return pd.read_csv(
        os.path.join(TEST_DATA_PATH, "reconciliation-net-ops-cashflows.csv")
    )


def test_financials_shares_outstanding(
    company_facts_dict, submissions_dict, shares_outstanding_recon
):

    sec_filling = SECFilings(
        companyfacts=company_facts_dict, submissions=submissions_dict
    )

    capex_values = (
        sec_filling.companyfacts.facts.us_gaap.CommonStockSharesOutstanding.units[
            "shares"
        ]
    )

    capex_values == shares_outstanding_recon.values.ravel().tolist()
