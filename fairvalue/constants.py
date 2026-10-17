import os

DATE_FORMAT = "%Y-%m-%d"
MEAN_DAYS_IN_YEAR = 365

NYSE = "NYSE"
NASDAQ = "NASDAQ"
CBOE = "CBOE"
EXCHANGES = [NYSE, NASDAQ, CBOE, "NONE"]

NET_CASHFLOW_OPS = "net_cashflow_ops"
CAPITAL_EXPENDITURE = "capital_expenditure"
SHARES_OUTSTANDING = "shares_outstanding"
FREE_CASHFLOW = "free_cashflows"

# bundled with the package so it resolves regardless of the working directory
PACKAGE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE_OF_INCORP_DICT = os.path.join(PACKAGE_DATA_DIR, "states_of_incorp.json")
