import pytest
from typing import get_type_hints, Union, Literal, Dict, Any

from fairvalue import Stock
from fairvalue.models.sec_ingestion import SECFilingsModel
from fairvalue.models.financials import ForecastTickerFinancials
from fairvalue._exceptions import FairValueException


def test_stock_invalid_initialization_no_ticker():
    """
    Test that the user-defined financials input method works
    where the user inputs all financials information.
    """
    with pytest.raises(
        FairValueException,
        match="ticker_id must be provided if sec_filing is None",
    ):

        historical_finances = {
            "operating_cashflows": [10],
            "capital_expenditures": [1],
            "year_end_dates": ["2020-01-01"],
            "free_cashflows": [-3],
            "shares_outstanding": [100],
        }

        Stock(
            exchange=["NASDAQ"],
            cik="123ABC",
            latest_shares_outstanding=3200,
            entity_name="test corp",
            historical_financials=historical_finances,
        )


def test_stock_invalid_initialization_no_financials():
    """
    Test that the user-defined financials input method works
    where the user inputs all financials information.
    """
    with pytest.raises(
        FairValueException,
        match="latest_shares_outstanding or historical_financials cannot both be None",
    ):

        Stock(
            ticker_id="test",
            exchange=["NASDAQ"],
            cik="123ABC",
            entity_name="test corp",
        )


# =============================================================================
# Test type hints
# =============================================================================


def test_stock_init_type_hints():
    """Test that the Stock class __init__ method has correct type hints."""
    hints = get_type_hints(Stock.__init__)

    assert hints["ticker_id"] == Union[str, None], "ticker_id should be str or None"
    assert (
        hints["exchange"] == Union[Literal["NYSE", "CBOE", "NASDAQ"], None]
    ), "exchange should be a Literal or None"
    assert hints["cik"] == Union[str, None], "cik should be str or None"
    assert (
        hints["latest_shares_outstanding"] == Union[int, None]
    ), "latest_shares_outstanding should be int or None"
    assert hints["entity_name"] == Union[str, None], "entity_name should be str or None"
    assert (
        hints["historical_financials"] == Union[Dict[str, Any], None]
    ), "historical_financials should be a dict or None"
    assert (
        hints["sec_filing"] == Union[SECFilingsModel, None]
    ), "sec_filing should be SECFilingsModel or None"


def test_stock_predict_fairvalue_type_hints():
    """Test that predict_fairvalue has correct type hints."""
    hints = get_type_hints(Stock.predict_fairvalue)

    assert hints["growth_rate"] == float, "growth_rate should be float"
    assert (
        hints["terminal_growth_rate"] == float
    ), "terminal_growth_rate should be float"
    assert hints["discounting_rate"] == float, "discounting_rate should be float"
    assert hints["number_of_years"] == int, "number_of_years should be int"
    assert hints["historical_features"] == bool, "historical_features should be bool"
    assert (
        hints["forecast_financials"] == Union[ForecastTickerFinancials, None]
    ), "forecast_financials should be ForecastTickerFinancials or None"
    assert (
        hints["forecast_date"] == Union[str, None]
    ), "forecast_date should be str or None"
    assert hints["use_historic_shares"] == bool, "use_historic_shares should be bool"
    assert hints["return"] == Dict[str, Any], "Return type should be dict"
