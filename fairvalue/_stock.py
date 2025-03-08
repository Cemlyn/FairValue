import datetime
from typing import List, Dict, Literal, Any

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

from fairvalue.constants import (
    DATE_FORMAT,
)

from fairvalue._exceptions import FairValueException
from fairvalue.models.sec_ingestion import SECFilingsModel
from fairvalue import utils


class Stock:

    def __init__(
        self,
        ticker_id: str | None = None,
        exchange: Literal["NYSE", "CBOE", "NASDAQ"] | None = None,
        cik: str | None = None,
        latest_shares_outstanding: int | None = None,
        entity_name: str | None = None,
        historical_financials: Dict[str, Any] | None = None,
        sec_filing: SECFilingsModel | None = None,
    ):
        """
        Initialize the Stock class with either SEC filing data or user-defined data.

        Args:
            ticker_id (str, optional): Stock ticker symbol
            exchange (str, optional): Stock exchange (NYSE, CBOE, or NASDAQ)
            cik (str, optional): SEC Central Index Key
            latest_shares_outstanding (int, optional): Most recent shares outstanding
            entity_name (str, optional): Company name
            historical_financials (Dict, optional): User-provided financial data
            sec_filing (SECFilingsModel, optional): SEC filing data model
        """
        if sec_filing:
            self._initialize_from_sec_filing(sec_filing)
        else:
            self._initialize_from_user_defined(
                ticker_id=ticker_id,
                exchange=exchange,
                cik=cik,
                entity_name=entity_name,
                latest_shares_outstanding=latest_shares_outstanding,
                historical_financials=historical_financials,
            )

        # Set shares outstanding after initialization
        if latest_shares_outstanding is None:
            self.latest_shares_outstanding = self.financials.shares_outstanding[-1]
        else:
            self.latest_shares_outstanding = latest_shares_outstanding

    def _initialize_from_user_defined(
        self,
        ticker_id: str | None,
        exchange: Literal["NYSE", "CBOE", "NASDAQ"] | None,
        cik: str | None,
        entity_name: str | None,
        latest_shares_outstanding: int | None,
        historical_financials: Dict[str, Any] | None,
    ):
        """Initialize stock attributes from user-defined data.

        Args:
            ticker_id (str): Stock ticker symbol
            exchange (str): Stock exchange
            cik (str): SEC Central Index Key
            entity_name (str): Company name
            latest_shares_outstanding (int): Number of shares outstanding
            historical_financials (Dict): User-provided financial data

        Raises:
            FairValueException: If required data is missing
        """
        if ticker_id is None:
            raise FairValueException("ticker_id must be provided if sec_filing is None")

        self.ticker_id = ticker_id
        self.exchange = exchange
        self.cik = cik
        self.entity_name = entity_name

        if (historical_financials is None) and (latest_shares_outstanding is None):
            raise FairValueException(
                "latest_shares_outstanding or historical_financials cannot both be None"
            )

        if historical_financials is not None:
            self.financials = TickerFinancials(**historical_financials)
        else:
            # Create minimal TickerFinancials with just shares outstanding
            self.financials = None

    def _initialize_from_sec_filing(self, sec_filing: SECFilingsModel):
        """Initialize stock attributes from SEC filing data.

        Args:
            sec_filing (SECFilingsModel): SEC filing data model
        """
        ticker_dict = dict(
            zip(sec_filing.submissions.tickers, sec_filing.submissions.exchanges)
        )
        shortest_key = min(ticker_dict, key=len)
        self.ticker_id = shortest_key
        self.exchange = ticker_dict[shortest_key]
        self.entity_name = sec_filing.companyfacts.entityName
        self.cik = sec_filing.companyfacts.cik

        if (
            hasattr(sec_filing, "date_of_latest_filing")
            and sec_filing.date_of_latest_filing is not None
        ):
            self.days_since_filing = (
                datetime.datetime.now().date()
                - datetime.datetime.strptime(
                    sec_filing.date_of_latest_filing, DATE_FORMAT
                ).date()
            ).days
            self.is_potentially_delisted = self.days_since_filing > 365
        else:
            self.date_of_latest_filing = None
            self.is_potentially_delisted = None

        self.financials = sec_filing.to_annual_financials()

    def predict_fairvalue(
        self,
        growth_rate: float = 0.00,
        terminal_growth_rate: float = 0.00,
        discounting_rate: float = 0.04,
        number_of_years: int = 10,
        historical_features: bool = False,
        forecast_financials: ForecastTickerFinancials | None = None,
        forecast_date: str | None = None,
        use_historic_shares: bool = False,
    ) -> Dict[str, Any]:
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

        response = dict()
        response["ticker_id"] = self.ticker_id
        response["exchange"] = self.exchange
        response["cik"] = self.cik
        response["entity_name"] = self.entity_name
        response["forecast_date"] = None
        response["forecast_horizon"] = number_of_years

        # If forecast financials not available generate using last years
        if forecast_financials is None:

            if forecast_date is None:
                forecast_date = datetime.datetime.now()
            else:
                forecast_date = datetime.datetime.strptime(forecast_date, DATE_FORMAT)

            response["forecast_date"] = forecast_date.strftime(DATE_FORMAT)

            latest_financials = fetch_latest_financials(
                date=forecast_date, financials=self.financials
            )

            # pylint: disable=too-many-locals
            if use_historic_shares:
                shares_outstanding = latest_financials.shares_outstanding[-1]
            else:
                shares_outstanding = self.latest_shares_outstanding

            if self.latest_shares_outstanding == 0:

                raise FairValueException(
                    "Unable to calculate FairValue. Shares outstanding is zero."
                )

            fcf = latest_financials.free_cashflows[-1]
            g = growth_rate

            free_cashflows = []

            for _ in range(number_of_years):
                fcf = fcf * (1 + g) / (1 + discounting_rate)
                free_cashflows.append(fcf)

            free_cashflows = Floats(data=free_cashflows)
            discount_rates = Floats(
                data=[discounting_rate for _ in range(number_of_years)]
            )

            year_end_dates = Strs(
                data=generate_future_dates(date=forecast_date, n=number_of_years)
            )

            forecast_financials = ForecastTickerFinancials(
                year_end_dates=year_end_dates,
                free_cashflows=free_cashflows,
                discount_rates=discount_rates,
                shares_outstanding=shares_outstanding,
                terminal_growth=terminal_growth_rate,
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

    if terminal_growth > discount[-1]:
        raise FairValueException(
            "Terminal growth rate must be less than the discounting rate."
        )

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
