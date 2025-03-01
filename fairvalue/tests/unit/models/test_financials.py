import pytest
import datetime

from pydantic import ValidationError

from fairvalue.models.financials import (
    TickerFinancials,
    fetch_latest_financials,
    latest_index,
)
from fairvalue._exceptions import FairValueException
from fairvalue.models.financials import ForecastTickerFinancials


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


@pytest.mark.parametrize(
    ("inputs", "expected_output"),
    [
        (
            (
                datetime.datetime(
                    year=2020, month=10, day=1, hour=0, minute=0, second=0
                ),
                [
                    "2018-01-01",
                    "2019-01-01",
                    "2020-01-01",
                    "2021-01-01",
                    "2022-01-01",
                    "2023-01-01",
                ],
            ),
            3,
        ),
        (
            (
                datetime.datetime(
                    year=2019, month=10, day=1, hour=0, minute=0, second=0
                ),
                [
                    "2018-01-01",
                    "2019-01-01",
                    "2020-01-01",
                    "2021-01-01",
                    "2022-01-01",
                    "2023-01-01",
                ],
            ),
            2,
        ),
        (
            (
                datetime.datetime(
                    year=2020, month=1, day=1, hour=0, minute=0, second=0
                ),
                ["2018-01-01", "2019-01-01", "2020-01-01"],
            ),
            3,
        ),
        (
            (
                datetime.datetime(
                    year=2020, month=1, day=1, hour=0, minute=0, second=1
                ),
                ["2018-01-01", "2019-01-01", "2020-01-01"],
            ),
            3,
        ),
        (
            (
                datetime.datetime(
                    year=2019, month=12, day=31, hour=23, minute=59, second=59
                ),
                ["2018-01-01", "2019-01-01", "2020-01-01"],
            ),
            2,
        ),
    ],
)
def test_latest_index_valid_input(inputs, expected_output):
    actual_output = latest_index(*inputs)
    assert actual_output == expected_output


def test_latest_invalid():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        FairValueException,
    ):
        latest_index(
            date=datetime.datetime(
                year=2019, month=12, day=31, hour=23, minute=59, second=59
            ),
            year_end_dates=["2020-01-01", "2021-01-01", "2022-01-01"],
        )


def test_latest_invalid2():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        FairValueException,
    ):
        latest_index(
            date=datetime.datetime(
                year=2019, month=12, day=31, hour=23, minute=59, second=59
            ),
            year_end_dates=[],
        )


def test_latest_financials():

    financials = TickerFinancials(
        year_end_dates=["2018-01-01", "2019-01-01", "2020-01-01"],
        free_cashflows=[-110, 10, 300],
        shares_outstanding=[10, 100, 100],
    )
    output = fetch_latest_financials(date="2019-12-30", financials=financials)

    assert output.year_end_dates is not None
    assert output.capital_expenditures is None
    assert output.operating_cashflows is None
    assert output.shares_outstanding is not None
    assert output.free_cashflows is not None
    assert len(output.year_end_dates) == 2

    financials = TickerFinancials(
        year_end_dates=["2018-01-01", "2019-01-01", "2020-01-01"],
        free_cashflows=[-110, 10, 300],
        capital_expenditures=[1, 1, 1],
        shares_outstanding=[10, 100, 100],
    )
    output = fetch_latest_financials(date="2019-12-30", financials=financials)

    assert output.year_end_dates is not None
    assert output.capital_expenditures is not None
    assert output.operating_cashflows is None
    assert output.shares_outstanding is not None
    assert output.free_cashflows is not None

    financials = TickerFinancials(
        year_end_dates=["2018-01-01", "2019-01-01", "2020-01-01"],
        free_cashflows=[-110, 10, 300],
        capital_expenditures=[1, 1, 1],
        operating_cashflows=[10, 10, 10],
        shares_outstanding=[10, 100, 100],
    )
    output = fetch_latest_financials(date="2019-12-30", financials=financials)

    assert output.year_end_dates is not None
    assert output.capital_expenditures is not None
    assert output.operating_cashflows is not None
    assert output.shares_outstanding is not None
    assert output.free_cashflows is not None

    financials = TickerFinancials(
        year_end_dates=["2018-01-01", "2019-01-01", "2020-01-01"],
        capital_expenditures=[1, 1, 1],
        operating_cashflows=[10, 10, 10],
        shares_outstanding=[10, 100, 100],
    )
    output = fetch_latest_financials(date="2019-12-30", financials=financials)

    assert output.year_end_dates is not None
    assert output.capital_expenditures is not None
    assert output.operating_cashflows is not None
    assert output.shares_outstanding is not None
    assert output.free_cashflows is not None

    financials = TickerFinancials(
        year_end_dates=["2018-01-01", "2019-01-01", "2020-01-01"],
        free_cashflows=[-110, 10, 300],
        shares_outstanding=[10, 100, 100],
    )
    output = fetch_latest_financials(date="2018-12-30", financials=financials)

    assert output.year_end_dates is not None
    assert output.capital_expenditures is None
    assert output.operating_cashflows is None
    assert output.shares_outstanding is not None
    assert output.free_cashflows is not None
    assert len(output.year_end_dates) == 1


# =============================================================================
# Forecast Financials
# =============================================================================


def test_forecast_ticker_initialisation_valid():
    ForecastTickerFinancials(
        year_end_dates=["2025-01-01", "2026-01-01"],
        free_cashflows=[1000, 1000],
        discount_rates=[0.04, 0.04],
        terminal_growth=0.02,
        shares_outstanding=1000,
    )


def test_forecast_ticker_different_sized_args():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        ValidationError,
    ):
        ForecastTickerFinancials(
            year_end_dates=["2025-01-01", "2026-01-01"],
            free_cashflows=[1000, 1000],
            discount_rates=[0.04],
            terminal_growth=0.02,
            shares_outstanding=1000,
        )


def test_forecast_ticker_negative_terminal_growth():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        ValidationError,
    ):
        ForecastTickerFinancials(
            year_end_dates=["2025-01-01", "2026-01-01"],
            free_cashflows=[1000, 1000],
            discount_rates=[0.04, 0.04],
            terminal_growth=-0.02,
            shares_outstanding=1000,
        )


def test_forecast_ticker_negative_share_count():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        ValidationError,
    ):
        ForecastTickerFinancials(
            year_end_dates=["2025-01-01", "2026-01-01"],
            free_cashflows=[1000, 1000],
            discount_rates=[0.04, 0.04],
            terminal_growth=0.02,
            shares_outstanding=-1000,
        )


def test_forecast_ticker_terminal_zero_shares_outstanding():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        ValidationError,
    ):
        ForecastTickerFinancials(
            year_end_dates=["2025-01-01", "2026-01-01"],
            free_cashflows=[1000, 1000],
            discount_rates=[0.04, 0.04],
            terminal_growth=0.02,
            shares_outstanding=0,
        )


def test_forecast_ticker_terminal_growth_gt_discount():
    """Test that USGaap model does not raise a Pydantic ValidationError."""
    with pytest.raises(
        ValidationError,
    ):
        ForecastTickerFinancials(
            year_end_dates=["2025-01-01", "2026-01-01"],
            free_cashflows=[1000, 1000],
            discount_rates=[0.04, 0.04],
            terminal_growth=0.05,
            shares_outstanding=1000,
        )
