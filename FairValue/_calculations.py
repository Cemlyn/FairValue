from datetime import (
    datetime,
)
from typing import (
    List,
    Tuple,
    Literal,
    Union,
)

import numpy as np
from sklearn.linear_model import (
    HuberRegressor,
    LinearRegression,
)
from fairvalue.constants import (
    DATE_FORMAT,
)


def daily_trend(
    dates: List[str] = None, amounts: List[float] = None
) -> Tuple[float, float, List[float]]:
    """
    Calculate the gradient (trend) in an amount in days.

    Args:
        dates (List[str]): A list of date strings in the format 'YYYY-MM-DD'.
        amounts (List[float]): A list of float or int amounts for the corresponding dates

    Returns:
        tuple: The gradient (slope) and intercept of the series
    """
    if not dates or not amounts:
        raise ValueError("Both 'dates' and 'amounts' must be provided.")
    if len(dates) != len(amounts):
        raise ValueError("'dates' and 'amounts' must have the same length.")

    # Convert dates to ordinal numbers for numerical analysis
    try:
        date_ordinals = [
            datetime.strptime(date, DATE_FORMAT).toordinal() for date in dates
        ]
    except ValueError as e:
        raise ValueError("Ensure all dates are in the format 'YYYY-MM-DD'.") from e

    for amount in amounts:
        if not isinstance(amount, (int, float)):
            raise ValueError(
                "Amounts must contains values which aren't of type 'int' or 'float'"
            )

    # Perform linear regression using numpy's polyfit
    slope, intercept = np.polyfit(date_ordinals, amounts, 1)

    # Calculate predicted values based on the trend line
    predicted = [slope * x + intercept for x in date_ordinals]

    # Calculate residuals
    residuals = [
        actual - pred
        for actual, pred in zip(
            amounts,
            predicted,
        )
    ]

    return slope, intercept, predicted, residuals


def detrend_series(
    dates: List[str] = None,
    amounts: List[Union[float, int]] = None,
    method: Literal["ols", "huber"] = "ols",
) -> List[float]:
    """
    Detrends a time series using linear regression.

    Args:
        dates (List[str]): A list of string-formatted dates.
        amounts (List[float]): A list of numerical values corresponding to the dates.
        method (str): The regression method to use ('ols' for ordinary least squares or 'huber' for robust regression).

    Returns:
        List[float]: A list of detrended values, where the linear trend has been removed.
    """
    if dates is None or amounts is None:
        raise ValueError("Both 'dates' and 'amounts' must be provided.")

    if len(dates) != len(amounts):
        raise ValueError("The length of 'dates' and 'amounts' must be equal.")

    if method not in [
        "ols",
        "huber",
    ]:
        raise ValueError("The 'method' argument must be either 'ols' or 'huber'.")

    # Convert dates to numeric values (e.g., days since the first date)
    date_numbers = [
        datetime.strptime(date, "%Y-%m-%d")
        - datetime.strptime(dates[0], "%Y-%m-%d").day
        for date in dates
    ]

    # Reshape for regression input
    x = np.array(date_numbers).reshape(-1, 1)
    y = np.array(amounts)

    models = {"ols": LinearRegression, "huber": HuberRegressor}

    model = models[method]
    model = model(fit_intercept=True)
    model.fit(x, y)
    trend = model.predict(x)

    # Subtract trend from the original series
    detrended_series = y - trend

    return detrended_series.tolist()
