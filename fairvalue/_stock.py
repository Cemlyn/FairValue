import datetime
from typing import List, Dict, Literal, Union

import numpy as np

from fairvalue.utils import (
    generate_future_dates,
    RoundedDict,
)
from fairvalue.models.financials import (
    TickerFinancials,
    ForecastTickerFinancials,
    fetch_latest_financials,
)
from fairvalue.models.base import Floats, Strs


from fairvalue._ingestion import secfiling_to_annual_financials

from fairvalue.constants import (
    DATE_FORMAT,
)

from fairvalue._exceptions import FairValueException
from fairvalue.models.ingestion import SECFilingsModel
from fairvalue import utils


class Stock:

    def __init__(
        self,
        ticker_id: str = None,
        exchange: Literal["NYSE", "CBOE", "NASDAQ", "NONE"] = "NONE",
        cik: str = None,
        latest_shares_outstanding: Union[int, None] = None,
        entity_name: str = None,
        historical_financials: dict = None,
        sec_filing: SECFilingsModel = None,
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

        if (
            (latest_shares_outstanding is None)
            and (historical_financials is None)
            and (sec_filing is None)
        ):
            raise FairValueException(
                "latest_shares_outstanding, or historical_financials or sec_filing must be provided."
            )

        if historical_financials:
            self.financials = TickerFinancials(**historical_financials)

        elif sec_filing:

            ticker_dict = dict(
                zip(sec_filing.submissions.tickers, sec_filing.submissions.exchanges)
            )
            shortest_key = min(ticker_dict, key=len)

            if self.ticker_id is None:
                self.ticker_id = shortest_key

            if self.exchange is None:
                self.exchange = ticker_dict[shortest_key]

            if self.entity_name is None:
                self.entity_name = sec_filing.companyfacts.entityName

            if self.cik is None:
                self.cik = sec_filing.companyfacts.cik

            self.date_of_latest_filing = sec_filing.date_of_latest_filing
            self.financials = secfiling_to_annual_financials(sec_filing=sec_filing)

        else:
            self.financials = None

        if latest_shares_outstanding is None:
            self.latest_shares_outstanding = self.financials.shares_outstanding[-1]
        else:
            self.latest_shares_outstanding = latest_shares_outstanding

    def predict_fairvalue(
        self,
        growth_rate: float = 0.00,
        growth_decay_rate: float = 0.00,
        discounting_rate: float = 0.05,
        number_of_years: int = 10,
        historical_features: bool = True,
        forecast_financials: ForecastTickerFinancials = None,
        forecast_date: str = None,
        use_historic_shares: bool = False,
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
        if forecast_date is None:
            forecast_date = datetime.datetime.now()
        else:
            forecast_date = datetime.datetime.strptime(forecast_date, DATE_FORMAT)

        latest_financials = fetch_latest_financials(
            date=forecast_date, financials=self.financials
        )

        if use_historic_shares:
            shares_outstanding = latest_financials.shares_outstanding[-1]
        else:
            shares_outstanding = self.latest_shares_outstanding

        response = dict()
        response["ticker_id"] = self.ticker_id
        response["exchange"] = self.exchange
        response["cik"] = self.cik
        response["entity_name"] = self.entity_name

        if hasattr(self, "date_of_latest_filing") and self.date_of_latest_filing:
            response["days_since_filing"] = (
                forecast_date.date()
                - datetime.datetime.strptime(
                    self.date_of_latest_filing, DATE_FORMAT
                ).date()
            ).days
            response["is_potentially_delisted"] = response["days_since_filing"] > 365

        response["count_filings"] = len(latest_financials.year_end_dates)
        response["forecast_date"] = forecast_date.strftime(DATE_FORMAT)
        response["forecast_horizon"] = number_of_years

        # If forecast financials not available generate using last years
        if forecast_financials is None:

            if self.latest_shares_outstanding == 0:

                raise FairValueException(
                    "Unable to calculate FairValue. Shares outstanding is zero."
                )

            fcf = latest_financials.free_cashflows[-1]
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
            year_end_dates = Strs(
                data=generate_future_dates(date=forecast_date, n=number_of_years)
            )

            forecast_financials = ForecastTickerFinancials(
                year_end_dates=year_end_dates,
                free_cashflows=free_cashflows,
                discount_rates=discount_rates,
                shares_outstanding=shares_outstanding,
                terminal_growth=g * (1 - growth_decay_rate),
            )

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


def calc_historical_features(financials: TickerFinancials = None) -> dict:

    features = dict()

    # check coverage
    missing_dates = utils.check_for_missing_dates(financials.year_end_dates)

    if missing_dates:
        return features

    # # Need at least 4 years of financials
    if len(financials.year_end_dates) < 4:
        return features

    # Auto correlation of freecashflows - used as a measure for stability
    features["fcf_autocorrelation"] = np.corrcoef(
        financials.free_cashflows[:-1], financials.free_cashflows[1:]
    )[0, 1]

    growth = [
        t1 / (t0 + 1) - 1
        for t0, t1 in zip(financials.free_cashflows[:-1], financials.free_cashflows[1:])
    ]
    features["median_fcf_growth_all"] = np.median(growth)

    growth = [
        t1 / (t0 + 1) - 1
        for t0, t1 in zip(
            financials.free_cashflows[-4:-1], financials.free_cashflows[-3:]
        )
    ]
    features["median_fcf_growth_l4y"] = np.median(growth)

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
    response["company_value"] = company_value

    intrinsic_value = np.where(
        shares_outstanding > 0, company_value / shares_outstanding, float("nan")
    )

    if isinstance(intrinsic_value, np.ndarray):
        intrinsic_value = intrinsic_value.item(0)

    response["intrinsic_value"] = intrinsic_value

    return response
