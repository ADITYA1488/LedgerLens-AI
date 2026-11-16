
import numpy as np
import pandas as pd


def calculate_prediction_interval(
    validation_actual,
    validation_predicted,
    future_forecast,
    confidence: float = 0.80
) -> pd.DataFrame:
    """
    Construct symmetric prediction intervals using
    absolute validation residuals.

    Calibration data must be separate from model training data.
    """

    actual = np.asarray(validation_actual, dtype=float).flatten()
    predicted = np.asarray(validation_predicted, dtype=float).flatten()
    forecast = np.asarray(future_forecast, dtype=float).flatten()

    if len(actual) != len(predicted):
        raise ValueError("Validation arrays must have equal lengths.")

    if len(actual) < 1:
        raise ValueError("Validation data cannot be empty.")

    if not np.isfinite(actual).all():
        raise ValueError("Actual values contain invalid numbers.")

    if not np.isfinite(predicted).all():
        raise ValueError("Predictions contain invalid numbers.")

    if not np.isfinite(forecast).all():
        raise ValueError("Future forecast contains invalid numbers.")

    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between 0 and 1.")

    absolute_errors = np.abs(actual - predicted)

    # Finite-sample conformal quantile.
    n = len(absolute_errors)
    rank = int(np.ceil((n + 1) * confidence))

    if rank > n:
        radius = np.inf
    else:
        radius = np.sort(absolute_errors)[rank - 1]

    return pd.DataFrame({
        "Forecast": forecast,
        "Lower_Bound": forecast - radius,
        "Upper_Bound": forecast + radius,
        "Interval_Radius": radius
    })


def calculate_interval_coverage(
    actual,
    lower_bound,
    upper_bound
) -> dict:
    """Measure empirical prediction interval coverage."""

    actual = np.asarray(actual, dtype=float).flatten()
    lower = np.asarray(lower_bound, dtype=float).flatten()
    upper = np.asarray(upper_bound, dtype=float).flatten()

    if not (len(actual) == len(lower) == len(upper)):
        raise ValueError("All arrays must have equal lengths.")

    if len(actual) == 0:
        raise ValueError("Inputs cannot be empty.")

    if not (
        np.isfinite(actual).all()
        and np.isfinite(lower).all()
        and np.isfinite(upper).all()
    ):
        raise ValueError("Inputs contain invalid numbers.")

    if np.any(lower > upper):
        raise ValueError("Lower bound cannot exceed upper bound.")

    covered = (actual >= lower) & (actual <= upper)

    return {
        "coverage": float(covered.mean()),
        "covered_count": int(covered.sum()),
        "total_count": int(len(actual))
    }
