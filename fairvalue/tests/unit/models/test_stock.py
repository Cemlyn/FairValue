import pytest
from fairvalue import Stock

from fairvalue._exceptions import FairValueException


def test_stock_invalid_initialization_no_ticker():
    """
    Test that the user-defined financials input method works
    where the user inputs all financials information.
    """
    with pytest.raises(
        FairValueException,
        match="ticker_id must be provided if sec_filing is not provided.",
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
        match="latest_shares_outstanding, or historical_financials or sec_filing must be provided.",
    ):

        Stock(
            ticker_id="test",
            exchange=["NASDAQ"],
            cik="123ABC",
            entity_name="test corp",
        )
