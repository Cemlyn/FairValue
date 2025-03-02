import pytest

from fairvalue import Stock
from fairvalue.models.ingestion import SECFilings
from fairvalue.models.financials import ForecastTickerFinancials


# =============================================================================
# SEC Filing Initialization Tests
# =============================================================================


@pytest.mark.parametrize("company", ["AAPL", "NVDA"])
def test_stock_initialization_with_sec_filing(company, sec_data):
    """
    Test that no errors are raised when initialising a stock with an SECFilings arg
    and correct financials are extracted from the SECFilings object.
    """
    sec_filling = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )
    stock = Stock(sec_filing=sec_filling)

    assert stock.ticker_id == company
    assert stock.cik == sec_filling.companyfacts.cik
    assert stock.entity_name == sec_filling.companyfacts.entityName

    reconciliation_file = sec_data["reconciliation-file"]

    assert (
        stock.financials.capital_expenditures
        == reconciliation_file["capital_expenditures"]
    )
    assert (
        stock.financials.shares_outstanding == reconciliation_file["shares_outstanding"]
    )
    assert stock.financials.year_end_dates == reconciliation_file["year_end_dates"]
    assert (
        stock.financials.operating_cashflows == reconciliation_file["net_ops_cashflows"]
    )
    assert stock.financials.free_cashflows == reconciliation_file["free_cashflows"]

    result = stock.predict_fairvalue()

    assert isinstance(result, dict)
    assert "intrinsic_value" in result
    assert isinstance(result["intrinsic_value"], float)


# =============================================================================
# User-Defined Financials Tests
# =============================================================================


def test_stock_initialization_with_user_financials():
    """
    Test that the user-defined financials input method works
    where the user inputs all financials information.
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
    assert stock.financials.capital_expenditures == [1]
    assert stock.financials.shares_outstanding == [100]
    assert stock.financials.year_end_dates == ["2020-01-01"]
    assert stock.financials.operating_cashflows == [10]
    assert stock.financials.free_cashflows == [-3]


def test_stock_initialization_with_user_financials_fcf_only():
    """
    Test that the user-defined financials input method works
    where the user inputs provides free cashflows only
    """
    historical_finances = {
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
    assert stock.financials.shares_outstanding == [100]
    assert stock.financials.year_end_dates == ["2020-01-01"]
    assert stock.financials.free_cashflows == [-3]


def test_stock_initialization_with_user_financials_no_fcf():
    """
    Test that the user-defined financials input method works
    where the user inputs provides free cashflows only
    """
    historical_finances = {
        "operating_cashflows": [10, 12],
        "capital_expenditures": [1, 2],
        "year_end_dates": ["2020-01-01", "2021-01-01"],
        "shares_outstanding": [100, 100],
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
    assert stock.financials.capital_expenditures == [1, 2]
    assert stock.financials.shares_outstanding == [100, 100]
    assert stock.financials.year_end_dates == ["2020-01-01", "2021-01-01"]
    assert stock.financials.operating_cashflows == [10, 12]
    assert stock.financials.free_cashflows == [9, 10]


def test_stock_initialization_with_no_financials_but_forecast():
    """
    Test that the user-defined financials input method works
    where the user inputs provides free cashflows only
    """

    stock = Stock(
        ticker_id="TEST",
        exchange=["NASDAQ"],
        cik="123ABC",
        latest_shares_outstanding=3200,
        entity_name="test corp",
    )

    assert stock.ticker_id == "TEST"
    assert stock.cik == "123ABC"

    forecast_financials = ForecastTickerFinancials(
        year_end_dates=["2025-01-01", "2026-01-01"],
        free_cashflows=[1000, 1000],
        discount_rates=[0.04, 0.04],
        terminal_growth=0.02,
        shares_outstanding=1000,
    )

    stock.predict_fairvalue(
        growth_rate=0.02,
        terminal_growth_rate=0.01,
        discounting_rate=0.04,
        number_of_years=10,
        forecast_financials=forecast_financials,
    )
