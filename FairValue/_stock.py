import warnings

from typing import List, Dict, Literal, Union, Tuple

import datetime

# from datetime import (
#     date,
# )
# from datetime import (
#     datetime,
# )

import numpy as np
import pandas as pd

from fairvalue.utils import (
    series_to_list,
    generate_future_dates,
    RoundedDict,
    drop_nans,
)
from fairvalue.models.financials import (
    TickerFinancials,
    ForecastTickerFinancials,
)
from fairvalue.models.base import Floats, Strs, NonNegInts, NonNegFloats

from fairvalue.models.utils import validate_date

from fairvalue._calculations import (
    daily_trend,
)

from fairvalue.constants import (
    DATE_FORMAT,
    MEAN_DAYS_IN_YEAR,
)

from fairvalue._exceptions import FairValueException


class Stock:

    def __init__(
        self,
        ticker_id: str = None,
        exchange: Literal["NYSE", "CBOE", "NASDAQ", "NONE"] = "NONE",
        cik: str = None,
        latest_shares_outstanding: Union[int, None] = None,
        entity_name: str = None,
        historical_financials: dict = None,
    ):
        """
        Initialize the CompanyFinancials class with a DataFrame.

        Args:
            dataframe (pd.DataFrame): DataFrame containing 'year', 'free_cashflow', 'capex', and 'shares_outstanding'.
        """

        self.ticker_id = ticker_id
        self.exchange = exchange
        self.cik = cik
        self.entity_name = entity_name

        if latest_shares_outstanding is None:
            raise FairValueException(
                "FairValue does not support tickers with zero shares outstanding."
            )
        self.latest_shares_outstanding = latest_shares_outstanding

        if historical_financials:
            self.financials = TickerFinancials(**historical_financials)
        else:
            self.financials = None

    def fetch_latest_financials(
        self, date: Union[str, datetime.date] = None
    ) -> TickerFinancials:

        if self.financials is None:
            raise ValueError(
                "Unable to fetch latest historical financials. finanicals are 'None'"
            )
        elif len(self.financials.free_cashflows) == 0:
            raise FairValueException(
                "Unable to fetch financials. financials have len zero."
            )

        if date is None:
            raise ValueError(
                "date must be string of format '%Y-%m-%d', or datetime.date object"
            )

        if isinstance(date, str):
            date = datetime.datetime.strptime(date, DATE_FORMAT)
        elif not isinstance(date, datetime.date):
            raise ValueError(
                "'date' must be string of format '%Y-%m-%d', or datetime.date object"
            )

        n = latest_index(date, self.financials.year_end_dates)

        free_cashflows = self.financials.free_cashflows[:n]
        year_end_dates = self.financials.year_end_dates[:n]
        shares_outstanding = [self.latest_shares_outstanding] * (n)

        if len(free_cashflows) == 0:
            raise ValueError(f"cemlyn error, date: {date}")

        if self.financials.capital_expenditures is not None:
            capital_expenditures = self.financials.capital_expenditures[:n]
            return TickerFinancials(
                free_cashflows=free_cashflows,
                capital_expenditures=capital_expenditures,
                year_end_dates=year_end_dates,
                shares_outstanding=shares_outstanding,
            )

        shares_series = [0.0] * (n)
        return TickerFinancials(
            free_cashflows=free_cashflows,
            year_end_dates=year_end_dates,
            capital_expenditures=shares_series,
            shares_outstanding=shares_outstanding,
        )

    def predict_fairvalue(
        self,
        growth_rate: float = 0.00,
        growth_decay_rate: float = 0.01,
        discounting_rate: float = 0.05,
        number_of_years: int = 10,
        historical_features: bool = True,
        forecast_financials: ForecastTickerFinancials = None,
    ) -> dict:
        """
        Generate a quick fairvalue estimate using the latest financials for a company, projecting
        them forward using a growth, growth decay rate and discounting rate

        Args:
            growth_rate (float): Project yoy growth for free cashflows
            growth_decay_rate (float): Add a second order gradient to the rate of change of
                free cashflows
            discounting_rate (float): rate of discounting to apply, i.e. the risk free rate
            number_of_years (int): number of years to project the forecast forward
            historical_features (bool): Return historical features along with the forecast

        Returns:
            dict: contains features and calclated intrinsic value.
        """

        # pylint: disable=too-many-locals
        today = datetime.datetime.now()

        financials = self.fetch_latest_financials(date=today)

        last_filing_date = datetime.datetime.strptime(
            financials.year_end_dates[-1], DATE_FORMAT
        ).date()

        response = dict()
        response["ticker_id"] = self.ticker_id
        response["exchange"] = self.exchange
        response["cik"] = self.cik
        response["entity_name"] = self.entity_name
        response["last_filing_date"] = financials.year_end_dates[-1]
        response["days_since_filiing"] = (today.date() - last_filing_date).days
        response["number_of_historical_filings"] = len(financials.year_end_dates)
        response["forecast_date"] = today.strftime(DATE_FORMAT)
        response["forecast_horizon"] = number_of_years

        # If forecast financials not available generate using last years
        if forecast_financials is None:

            if self.latest_shares_outstanding == 0:

                raise FairValueException(
                    "Unable to calculate FairValue. Shares outstanding is zero."
                )

            fcf = self.financials.free_cashflows[-1]
            g = growth_rate

            free_cashflows = []

            for _ in range(number_of_years):
                fcf = fcf * (1 + g) / (1 + discounting_rate)
                g = g * (1 - growth_decay_rate)
                free_cashflows.append(fcf)

            free_cashflows = Floats(data=free_cashflows)
            discount_rates = Floats(
                data=[discounting_rate for _ in range(number_of_years)]
            )
            # shares_outstanding = self.latest_shares_outstanding
            year_end_dates = Strs(data=generate_future_dates(n=number_of_years))

            forecast_financials = ForecastTickerFinancials(
                year_end_dates=year_end_dates,
                free_cashflows=free_cashflows,
                discount_rates=discount_rates,
                shares_outstanding=self.latest_shares_outstanding,
                terminal_growth=g * (1 - growth_decay_rate),
            )

        else:
            forecast_financials = self.forecast_financials

        intrinsic_value = calc_intrinsic_value(
            free_cashflows=forecast_financials.free_cashflows,
            discount=forecast_financials.discount_rates,
            terminal_growth=forecast_financials.terminal_growth,
            shares_outstanding=forecast_financials.shares_outstanding,
        )
        response.update(intrinsic_value)

        # calculate features
        if historical_features and self.financials is not None:
            features = calc_historical_features(self.financials)
            response.update(features)

        # pylint: enable=too-many-locals

        return dict(RoundedDict(response)._dict)


def latest_index(date: datetime.datetime, year_end_dates: List[str]):

    l = len(year_end_dates) - 1

    for n, x in enumerate(year_end_dates):

        year_end_date_obj = datetime.datetime.strptime(x, DATE_FORMAT)

        if date < year_end_date_obj:

            if n == 0:
                raise FairValueException(
                    f"Unable to retrieve financials before the date '{date}'"
                )
            return n

    return n + 1


def calc_historical_features(financials: TickerFinancials = None) -> dict:

    features = dict()

    # Free Cashflow trends
    dates, fc_flows = drop_nans(financials.year_end_dates, financials.free_cashflows)

    # free cashflow features which looks at trends in the financials
    features["free_cashflow_yoy_amt"] = (
        np.nan if len(fc_flows) < 2 else (fc_flows[-1] - fc_flows[-2])
    )
    features["free_cashflow_yoy_pct"] = (
        np.nan
        if (len(fc_flows) < 2) or (fc_flows[-2] == 0)
        else (fc_flows[-1] / fc_flows[-2] - 1)
    )

    # last 3, 5, 10 years
    for n in [3, 5, 10]:
        fc_flows_slice = fc_flows[:n]
        dates_slice = dates[:n]
        features[f"free_cashflow_range_L{n}yrs"] = max(fc_flows_slice) - min(
            fc_flows_slice
        )
        features[f"free_cashflow_trend_L{n}yrs"], _, _, residuals = daily_trend(
            dates_slice, fc_flows_slice
        )
        features[f"free_cashflow_trend_L{n}yrs"] = (
            features[f"free_cashflow_trend_L{n}yrs"] * MEAN_DAYS_IN_YEAR
        )
        features[f"free_cashflow_detrended_range_L{n}yrs"] = max(residuals) - min(
            residuals
        )
        features[f"free_cashflow_detrended_std_L{n}yrs"] = np.std(residuals)
        features[f"free_cashflow_perc_gt_zero_L{n}yrs"] = len(
            [x for x in fc_flows_slice if x > 0]
        ) / len(fc_flows_slice)

        free_cashflows_yoy = [
            b - a for a, b in zip(fc_flows_slice[:-1], fc_flows_slice[1:])
        ]
        features[f"free_cashflow_perc_non_zero_growth_L{n}yrs"] = (
            np.nan
            if len(free_cashflows_yoy) == 0
            else len([x for x in free_cashflows_yoy if x > 0]) / len(free_cashflows_yoy)
        )

    features = dict()

    return features


def calc_intrinsic_value(
    free_cashflows: List[float],
    discount: List[float],
    terminal_growth: float,
    shares_outstanding: int,
) -> Dict[str, float]:
    """
    Calculate the intrinsic value of a series of free cash flows using
    the Discounted Cash Flow (DCF) method.

    Args:
        free_cashflows (list): List of free cash flows for the forecast period.
        growth (list): Annual growth rates for free cash flows (in decimal, e.g., 0.05 for 5%).
        discount (list): Annual discount rates (in decimal, e.g., 0.1 for 10%).
        terminal_growth (float): Terminal growth rate (in decimal, e.g., 0.03 for 3%).

    Returns:
        float: The intrinsic value of the cash flows.
    """

    # Calculate the present value of forecasted free cash flows
    present_value_fcf = 0
    for i in range(len(free_cashflows)):
        discounted_fcf = max(
            free_cashflows[i] / (1 + discount[i]) ** (i + 1),
            0,
        )
        present_value_fcf += discounted_fcf

    # Calculate the terminal value
    terminal_value = (
        free_cashflows[-1] * (1 + terminal_growth) / (discount[-1] - terminal_growth)
    )

    # Discount the terminal value to present
    present_value_terminal = terminal_value / (1 + discount[-1]) ** len(free_cashflows)

    # Total intrinsic value
    company_value = present_value_fcf + present_value_terminal

    response = {}
    response["shares_outstanding"] = shares_outstanding
    response["latest_free_cashflow"] = free_cashflows[-1]
    response["company_value"] = company_value

    intrinsic_value = np.where(
        shares_outstanding > 0, company_value / shares_outstanding, float("nan")
    )

    if isinstance(intrinsic_value, np.ndarray):
        intrinsic_value = intrinsic_value.item(0)

    response["intrinsic_value"] = intrinsic_value

    return response
