
import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.stats.diagnostic import acorr_ljungbox


def forecast_financial_series(
    series: pd.Series,
    horizon: int = 1,
    method: str = "holt_winters"
) -> dict:
    """
    Forecast a monthly financial time series.

    Parameters
    ----------
    series : pd.Series
        Monthly financial values with a DatetimeIndex.
    horizon : int
        Number of future months to forecast.
    method : str
        'holt_winters' or 'moving_average_3'.

    Returns
    -------
    dict
        Forecast, fitted model, parameters and residual diagnostics.
    """

    if not isinstance(series, pd.Series):
        raise TypeError("series must be a pandas Series.")

    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("Series index must be a DatetimeIndex.")

    if horizon < 1:
        raise ValueError("horizon must be at least 1.")

    if series.index.has_duplicates:
        raise ValueError("Duplicate dates found in the series.")

    series = series.sort_index().astype(float).asfreq("ME")

    if series.isna().any():
        raise ValueError(
            "Missing monthly observations found. "
            "Resolve them before forecasting."
        )

    if not np.isfinite(series.to_numpy()).all():
        raise ValueError("Series contains infinite values.")

    if method == "holt_winters":

        if len(series) < 24:
            raise ValueError(
                "Holt-Winters requires at least 24 monthly observations."
            )

        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated"
        )

        fitted = model.fit(optimized=True)

        forecast = fitted.forecast(horizon)
        residuals = fitted.resid.dropna()

        params = fitted.params

        diagnostics = acorr_ljungbox(
            residuals,
            lags=[6, 12],
            return_df=True
        )

        return {
            "forecast": forecast,
            "model": fitted,
            "method": method,
            "parameters": params,
            "residuals": residuals,
            "diagnostics": diagnostics
        }

    elif method == "moving_average_3":

        if len(series) < 3:
            raise ValueError(
                "Moving average requires at least 3 observations."
            )

        forecast_value = series.tail(3).mean()

        forecast_index = pd.date_range(
            start=series.index[-1] + pd.offsets.MonthEnd(1),
            periods=horizon,
            freq="ME"
        )

        forecast = pd.Series(
            forecast_value,
            index=forecast_index
        )

        return {
            "forecast": forecast,
            "model": None,
            "method": method,
            "parameters": {
                "window": 3
            },
            "residuals": None,
            "diagnostics": None
        }

    else:
        raise ValueError(
            "Unsupported method. Use 'holt_winters' or 'moving_average_3'."
        )
