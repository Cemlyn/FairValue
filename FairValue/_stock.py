import warnings

from typing import List, Dict, Tuple, Literal
from datetime import (
    date,
)
from datetime import (
    datetime,
)

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
from fairvalue.models.base import (
    Floats,
    Strs,
    NonNegInts,
)
from fairvalue._calculations import (
    daily_trend,
    detrend_series,
)

from fairvalue.constants import (
    DATE_FORMAT,
    MEAN_DAYS_IN_YEAR,
)


class Stock:

    def __init__(
        self,
        ticker_id: str = None,
        exchange: Literal["NYSE", "CBOE", "NASDAQ", "NONE"] = "NONE",
        cik: str = None,
        entityName: str = None,
        historical_financials: dict = None,
        forecasted_financials: dict = None,
    ):
        """
        Initialize the CompanyFinancials class with a DataFrame.

        Args:
            dataframe (pd.DataFrame): DataFrame containing 'year', 'free_cashflow', 'capex', and 'shares_outstanding'.
        """

        self.ticker_id = ticker_id
        self.exchange = exchange
        self.cik = cik
        self.entityName = entityName

        if historical_financials:
            self.financials = TickerFinancials(**historical_financials)
        else:
            self.financials = None

        if forecasted_financials:
            self.forecast_financials = ForecastTickerFinancials(**forecasted_financials)
        else:
            self.forecast_financials = None

    def predict_fairvalue(
        self,
        growth_rate: float = 0.00,
        growth_decay_rate: float = 0.01,
        discounting_rate: float = 0.05,
        number_of_years: int = 10,
        historical_features: bool = True,
    ) -> dict:

        today = date.today()
        last_filing_date = datetime.strptime(
            self.financials.year_end_dates[-1],
            DATE_FORMAT,
        ).date()

        response = dict()
        response["ticker_id"] = self.ticker_id
        response["exchange"] = self.exchange
        response["cik"] = self.cik
        response["entityName"] = self.entityName
        response["last_filing_date"] = self.financials.year_end_dates[-1]
        response["days_since_filiing"] = (today - last_filing_date).days
        response["number_of_historical_filings"] = len(self.financials.year_end_dates)
        response["forecast_date"] = today.strftime(DATE_FORMAT)
        response["forecast_horizon"] = number_of_years

        # If forecast financials not available generate using last years
        if not self.forecast_financials:

            warnings.warn(
                "No forecast financials provided. Historical financials \
                    will be used to generate forecasts.",
                category=UserWarning,
            )

            if self.financials is None:
                raise ValueError(
                    "Fairvalue forecast cannot be made as no forecast financials \
                        or historical financials have been provided."
                )

            if self.financials.shares_outstanding[-1] == 0:

                warnings.warn(
                    "FairValue cannot be made as there are no shares outstanding as of the \
                        last 10-K filing. Returning incomplete fair value calculation.",
                    category=UserWarning,
                )
                return response

            fcf = self.financials.free_cashflows[-1]
            g = growth_rate

            free_cashflows = []

            for _ in range(number_of_years):
                fcf = fcf * (1 + g) / (1 + discounting_rate)
                g = g * (1 - growth_decay_rate)
                free_cashflows.append(fcf)

            free_cashflows = Floats(data=free_cashflows)
            discount_rates = Floats(data=[discounting_rate for _ in range(number_of_years)])
            shares_outstanding = self.financials.shares_outstanding[-1]
            year_end_dates = Strs(data=generate_future_dates(n=number_of_years))

            forecast_financials = ForecastTickerFinancials(
                year_end_dates=year_end_dates,
                free_cashflows=free_cashflows,
                discount_rates=discount_rates,
                shares_outstanding=shares_outstanding,
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

        return RoundedDict(response)._dict


def calc_historical_features(
    financials: TickerFinancials = None,
) -> dict:

    features = dict()

    # Free Cashflow trends
    (
        dates,
        fc_flows,
    ) = drop_nans(
        financials.year_end_dates,
        financials.free_cashflows,
    )

    # free cashflow features which looks at trends in the financials
    features["free_cashflow_yoy_amt"] = np.nan if len(fc_flows) < 2 else (fc_flows[-1] - fc_flows[-2])
    features["free_cashflow_yoy_pct"] = np.nan if (len(fc_flows) < 2) or (fc_flows[-2] == 0) else (fc_flows[-1] / fc_flows[-2] - 1)

    # last 3, 5, 10 years
    for n in [
        3,
        5,
        10,
    ]:
        fc_flows_slice = fc_flows[:n]
        dates_slice = dates[:n]
        # features[f"free_cashflow_mean_L{n}yrs"] = np.mean(fc_flows_slice)
        # features[f"free_cashflow_median_L{n}yrs"] = np.median(fc_flows_slice)
        # features[f"free_cashflow_std_L{n}yrs"] = np.std(fc_flows_slice)
        features[f"free_cashflow_range_L{n}yrs"] = max(fc_flows_slice) - min(fc_flows_slice)
        (
            features[f"free_cashflow_trend_L{n}yrs"],
            _,
            _,
            residuals,
        ) = daily_trend(
            dates_slice,
            fc_flows_slice,
        )
        features[f"free_cashflow_trend_L{n}yrs"] = features[f"free_cashflow_trend_L{n}yrs"] * MEAN_DAYS_IN_YEAR
        features[f"free_cashflow_detrended_range_L{n}yrs"] = max(residuals) - min(residuals)
        features[f"free_cashflow_detrended_std_L{n}yrs"] = np.std(residuals)
        features[f"free_cashflow_perc_gt_zero_L{n}yrs"] = len([x for x in fc_flows_slice if x > 0]) / len(fc_flows_slice)

        free_cashflows_yoy = [b - a for a, b in zip(fc_flows_slice[:-1], fc_flows_slice[1:])]
        features[f"free_cashflow_perc_non_zero_growth_L{n}yrs"] = np.nan if len(free_cashflows_yoy) == 0 else len([x for x in free_cashflows_yoy if x > 0]) / len(free_cashflows_yoy)

    return features


def calc_intrinsic_value(
    free_cashflows: List[float],
    discount: List[float],
    terminal_growth: float,
    shares_outstanding: int,
) -> Dict[
    str,
    float,
]:
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
    terminal_value = free_cashflows[-1] * (1 + terminal_growth) / (discount[-1] - terminal_growth)

    # Discount the terminal value to present
    present_value_terminal = terminal_value / (1 + discount[-1]) ** len(free_cashflows)

    # Total intrinsic value
    company_value = present_value_fcf + present_value_terminal

    response = {}
    response["shares_outstanding"] = shares_outstanding
    response["future_cashflows"] = present_value_fcf
    response["terminal_value"] = terminal_value
    response["company_value"] = company_value
    response["intrinsic_value"] = max(
        0,
        company_value,
    ) / max(
        1,
        shares_outstanding,
    )

    return response


def cfacts_df_to_dict(
    df: pd.DataFrame,
) -> Dict[
    str,
    List,
]:

    company_facts = dict()
    company_facts["operating_cashflows"] = Floats(data=series_to_list(df.net_cashflow_ops.astype(float)))
    company_facts["capital_expenditures"] = Floats(data=series_to_list(df.capital_expenditure.astype(float)))
    company_facts["year_end_dates"] = Strs(data=series_to_list(df["end"]))
    company_facts["shares_outstanding"] = NonNegInts(data=series_to_list(df.shares_outstanding.astype(int)))

    if "free_cashflows" in df:

        company_facts["free_cashflows"] = Floats(data=series_to_list(df.free_cashflows.astype(float)))

    return company_facts
