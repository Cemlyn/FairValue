import tqdm
import pandas as pd
import numpy as np

from matplotlib import pyplot as plt
from matplotlib import axes

from utils import series_to_list
from models.stock import TickerFinancials, ScenarioParams
from models.base import Floats, Strs, NonNegFloats, NonNegInts


class Stock:

    def __init__(self, ticker: str, ticker_financials: TickerFinancials = None):
        """
        Initialize the CompanyFinancials class with a DataFrame.

        Args:
            dataframe (pd.DataFrame): DataFrame containing 'year', 'free_cashflow', 'capex', and 'shares_outstanding'.
        """
        self.ticker_id = ticker
        self.financials = ticker_financials
        self.financial_dates = ticker_financials.year_end_dates
        self.latest_financial_date = max(self.financial_dates)

    def plot_financial(self,financial_id: str='capex') -> axes:

        if self.financials is None:
            raise ValueError('Financials have not been loaded.')

        if financial_id == 'capex':
            capex_series = self.financials.capital_expenditures
            _,axes = plt.subplots(1,1)
            pd.Series(capex_series, index=self.financial_dates).sort_index().plot.bar(ax=axes)
            axes.set_title('Capital Expenditure')
            return axes

        if financial_id == 'ops_cashflow':
            capex_series = self.financials.capital_expenditures
            _,axes = plt.subplots(1,1)
            pd.Series(capex_series, index=self.financial_dates).sort_index().plot.bar(ax=axes)
            axes.set_title('Cashflow from Operations')
            return axes

    def run_scenario_from_params(self, scenario_params: ScenarioParams = None) -> float:

        if scenario_params is None:
            years = 10
            fcf = self.financials.free_cashflows[-1]
            shares = self.financials.shares_outstanding[-1]

            if (fcf in [None,np.nan]) or (shares in [None,np.nan]):
                return None

            scenario_params = ScenarioParams(free_cashflows=Floats(data=[fcf for _ in range(years)]),
                           discount_rates=NonNegFloats(data=[0.05 for _ in range(years)]),
                           growth_rates=Floats(data=[0.03 for _ in range(years)]),
                           terminal_growth_rate=0.02,
                           shares_outstanding = NonNegInts(data=[shares for _ in range(years)])
                           )

        intrinsic_value = calc_intrinsic_value(scenario_params.free_cashflows,
                             scenario_params.growth_rates,
                             scenario_params.discount_rates,
                             scenario_params.terminal_growth_rate)

        return 0 if shares in [None,0] else round(intrinsic_value/shares,2)

class Stocks:
    def __init__(self, filepath):

        self.stocks = dict()
        self.filepath = filepath

        df = pd.read_json(filepath,lines=True)
        df = df[~df['ticker'].isna()]

        for ticker_id,ticker_df in tqdm.tqdm(df.groupby('ticker')):
            ticker_financials = cfacts_to_tfinancials(ticker_df)
            self.stocks[ticker_id] = Stock(ticker=ticker_id, ticker_financials=ticker_financials)
    
    def generate_value_data(self,):
        data = dict()
        for ticker_id,stock in self.stocks.items():
            data[ticker_id] = stock.run_scenario_from_params()
        return data


def calc_intrinsic_value(
    free_cashflows: list, growth: list, discount: list, terminal_growth: float
) -> float:
    """
    Calculate the intrinsic value of a series of free cash flows using the Discounted Cash Flow (DCF) method.
    
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
        discounted_fcf = max(free_cashflows[i] / (1 + discount[i]) ** (i + 1),0)
        present_value_fcf += discounted_fcf

    # Calculate the terminal value
    last_fcf = max(free_cashflows[-1] * (1 + growth[-1]),0)  # Last FCF grows by the last year's growth rate
    terminal_value = last_fcf * (1 + terminal_growth) / (discount[-1] - terminal_growth)

    # Discount the terminal value to present
    present_value_terminal = terminal_value / (1 + discount[-1]) ** len(free_cashflows)

    # Total intrinsic value
    intrinsic_value = present_value_fcf + present_value_terminal

    return intrinsic_value


def cfacts_to_tfinancials(df: pd.DataFrame) -> TickerFinancials:

    op_cf = Floats(data=series_to_list(df.net_cashflow_ops.astype(float)))
    cap_ex = Floats(data=series_to_list(df.capital_expenditure.astype(float)))
    year_end_dates=Strs(data=series_to_list(df['end']))
    shares_outstanding=NonNegInts(data=series_to_list(df.shares_outstanding.astype(int)))

    if 'free_cashflow' not in df:

        tf = TickerFinancials(operating_cashflows=op_cf,
                            capital_expenditures=cap_ex,
                            year_end_dates=year_end_dates,
                            shares_outstanding=shares_outstanding)
    
    else:

        free_cf = Floats(data=series_to_list(df.free_cashflow.astype(float)))

        tf = TickerFinancials(operating_cashflows=op_cf,
                            capital_expenditures=cap_ex,
                            year_end_dates=year_end_dates,
                            free_cashflows=free_cf,
                            shares_outstanding=shares_outstanding)

    return tf

if __name__ == "__main__":
    import pickle
    stocks = Stocks("company_facts.jsonl")
    stocks.generate_value_data()
    with open('stocks.pkl','wb') as file:
        pickle.dump(stocks, file)
