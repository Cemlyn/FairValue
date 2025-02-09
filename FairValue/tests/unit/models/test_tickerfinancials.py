import pytest

from pydantic import ValidationError

from fairvalue.models.financials import TickerFinancials


def test_invalid_ticker_no_capex():

    with pytest.raises(
        ValidationError,
    ):
        TickerFinancials(
            operating_cashflows=[-10.0, 10.0, -10.2, 1.4, 20.2],
            year_end_dates=[
                "2020-01-01",
                "2021-01-01",
                "2022-01-01",
                "2023-01-01",
                "2024-01-01",
            ],
            shares_outstanding=[1, 1, 1, 1, 1],
        )


def test_valid_ticker_incl_capex():

    try:
        TickerFinancials(
            operating_cashflows=[-10.0, 10.0, -10.0, 10.0, 20.0],
            year_end_dates=[
                "2020-01-01",
                "2021-01-01",
                "2022-01-01",
                "2023-01-01",
                "2024-01-01",
            ],
            capital_expenditures=[1.0, 1.0, 1.0, 1.0, 1.0],
            shares_outstanding=[1, 1, 1, 1, 1],
        )
    except ValidationError as e:
        pytest.fail(f"Unexpected Pydantic ValidationError raised: {e}")


def test_invalid_ticker_missing_ops_cashflow():

    with pytest.raises(
        ValidationError,
    ):
        TickerFinancials(
            year_end_dates=[
                "2020-01-01",
                "2021-01-01",
                "2022-01-01",
                "2023-01-01",
                "2024-01-01",
            ],
            capital_expenditures=[1.0, 1.0, 1.0, 1.0, 1.0],
            shares_outstanding=[1, 1, 1, 1, 1],
        )
