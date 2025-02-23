import os
import pytest

import pandas as pd

from fairvalue import Stock
from fairvalue.utils import load_json
from fairvalue.models.ingestion import SECFilings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_PATH = os.path.join(BASE_DIR, "..", "data", "APPL")


def test_predict_fairvalue_with_full_financials():
    """
    Test that the user-defined financials input method works
    where the user inputs capital expenditure and operating cashflows only.
    """

    historical_finances = {
        "operating_cashflows": [10],
        "capital_expenditures": [1],
        "year_end_dates": ["2020-01-01"],
        "free_cashflows": [-3],
        "shares_outstanding": [100],
    }

    stock = Stock(
        ticker_id="TEST",
        exchange=["NASDAQ"],
        cik="123ABC",
        latest_shares_outstanding=3200,
        entity_name="test corp",
        historical_financials=historical_finances,
    )

    assert stock.ticker_id == "TEST"
    assert stock.cik == "123ABC"

    stock.predict_fairvalue()


def test_predict_fairvalue_with_capex_and_ops_cashflow():
    """
    Test that the user-defined financials input method works
    where the user inputs capital expenditure and operating cashflows only.
    """

    historical_finances = {
        "operating_cashflows": [10],
        "capital_expenditures": [1],
        "year_end_dates": ["2020-01-01"],
        "shares_outstanding": [100],
    }

    stock = Stock(
        ticker_id="TEST",
        exchange=["NASDAQ"],
        cik="123ABC",
        latest_shares_outstanding=3200,
        entity_name="test corp",
        historical_financials=historical_finances,
    )

    assert stock.ticker_id == "TEST"
    assert stock.cik == "123ABC"

    stock.predict_fairvalue()


def test_predict_fairvalue_with_free_cashflow_only():
    """
    Test that the user-defined input method works
    when the user inputs free_cashflows only.
    """

    financials = {
        "year_end_dates": ["2025-01-01"],
        "free_cashflows": [108807000000],
        "shares_outstanding": [15115823000],
    }

    stock = Stock(ticker_id="AAPL", historical_financials=financials)

    stock.predict_fairvalue(growth_rate=0.02, number_of_years=10, discounting_rate=0.04)


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


def test_initialization_with_sec_filing(company_facts_dict, submissions_dict):
    """
    Test that no errors are raised when initialising a stock with an SECFillings arg.
    """

    sec_filling = SECFilings(
        companyfacts=company_facts_dict, submissions=submissions_dict
    )
    stock = Stock(sec_filing=sec_filling)

    assert stock.ticker_id == "AAPL"
    assert stock.entity_name == "Apple Inc."
    assert stock.cik == "320193"

    stock.predict_fairvalue()


def test_financials_with_sec_filing(company_facts_dict, submissions_dict):
    """
    Test that no errors are raised when initialising a stock with an SECFillings arg.
    """

    sec_filling = SECFilings(
        companyfacts=company_facts_dict, submissions=submissions_dict
    )
    stock = Stock(sec_filing=sec_filling)

    assert stock.ticker_id == "AAPL"
    assert stock.entity_name == "Apple Inc."
    assert stock.cik == "320193"

    stock.predict_fairvalue()
