import os
import pytest

import pandas as pd
from pydantic import ValidationError

from fairvalue import Stock
from fairvalue.utils import load_json
from fairvalue.models.ingestion import SECFilings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_stock():

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


def test_stock_2():

    financials = {
        "year_end_dates": ["2025-01-01"],
        "free_cashflows": [108807000000],
        "shares_outstanding": [15115823000],
    }

    stock = Stock(ticker_id="AAPL", historical_financials=financials)

    stock.predict_fairvalue(growth_rate=0.02, number_of_years=10, discounting_rate=0.04)


@pytest.fixture
def company_facts():
    return load_json(os.path.join(BASE_DIR, "data", "companyfacts-CIK0000320193.json"))


@pytest.fixture
def submissions():
    return load_json(os.path.join(BASE_DIR, "data", "submissions-CIK0000320193.json"))


def test_stock_name(company_facts, submissions):

    sec_filling = SECFilings(companyfacts=company_facts, submissions=submissions)
    stock = Stock(sec_filing=sec_filling)

    assert stock.ticker_id == "AAPL"
    assert stock.entity_name == "Apple Inc."
    assert stock.cik == "320193"


def test_stock_fairvalue(company_facts, submissions):

    sec_filling = SECFilings(companyfacts=company_facts, submissions=submissions)
    stock = Stock(sec_filing=sec_filling)
    result = stock.predict_fairvalue()
