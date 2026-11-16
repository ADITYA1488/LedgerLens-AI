
import numpy as np
import pandas as pd


def evaluate_forecast(actual, predicted) -> dict:
    """
    Evaluate a financial forecasting model.

    Parameters
    ----------
    actual : array-like
        Actual observed values.
    predicted : array-like
        Forecasted values.

    Returns
    -------
    dict
        MAE, RMSE, MAPE, sMAPE and forecast bias.
    """

    actual = np.asarray(actual, dtype=float).flatten()
    predicted = np.asarray(predicted, dtype=float).flatten()

    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted lengths must match.")

    if len(actual) == 0:
        raise ValueError("Inputs cannot be empty.")

    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Inputs contain NaN or infinite values.")

    errors = actual - predicted

    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))

    # MAPE is undefined when actual values are zero.
    nonzero_mask = actual != 0

    mape = (
        np.mean(
            np.abs(errors[nonzero_mask] / actual[nonzero_mask])
        ) * 100
        if nonzero_mask.any()
        else np.nan
    )

    # sMAPE handles zero actual values more safely.
    denominator = np.abs(actual) + np.abs(predicted)

    smape_values = np.divide(
        2 * np.abs(errors),
        denominator,
        out=np.zeros_like(errors),
        where=denominator != 0
    )

    smape = np.mean(smape_values) * 100

    # Positive bias = underforecasting.
    # Negative bias = overforecasting.
    bias = np.mean(errors)

    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "MAPE": float(mape),
        "sMAPE": float(smape),
        "Bias": float(bias)
    }


def evaluate_multiple_forecasts(results: dict) -> pd.DataFrame:
    """
    Evaluate multiple named forecasts.

    results format:
    {
        "Model A": (actual_values, predicted_values),
        "Model B": (actual_values, predicted_values)
    }
    """

    rows = []

    for model_name, (actual, predicted) in results.items():

        metrics = evaluate_forecast(actual, predicted)

        rows.append({
            "Model": model_name,
            **metrics
        })

    return pd.DataFrame(rows).set_index("Model")
