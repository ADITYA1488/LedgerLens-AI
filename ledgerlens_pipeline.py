
from forecasting import forecast_financial_series
from evaluation import evaluate_forecast
from intervals import calculate_prediction_interval
from model_registry import ModelRegistry


def run_forecasting_pipeline(
    series,
    entity,
    target,
    method="holt_winters",
    horizon=1,
    validation_actual=None,
    validation_predicted=None
):
    """Run and save a complete LedgerLens forecasting workflow."""

    result = forecast_financial_series(
        series=series,
        horizon=horizon,
        method=method
    )

    forecast = result["forecast"]

    evaluation = None
    intervals = None

    if validation_actual is not None and validation_predicted is not None:

        evaluation = evaluate_forecast(
            validation_actual,
            validation_predicted
        )

        intervals = calculate_prediction_interval(
            validation_actual,
            validation_predicted,
            forecast.values
        )

    registry = ModelRegistry()

    model_name = f"{entity.lower()}_{target.lower()}_{method}"

    if result["model"] is not None:
        registry.save_model(
            result["model"],
            model_name,
            metadata={
                "entity": entity,
                "target": target,
                "method": method,
                "frequency": "monthly",
                "training_end": str(series.index[-1].date())
            }
        )

    return {
        "entity": entity,
        "target": target,
        "method": method,
        "forecast": forecast,
        "evaluation": evaluation,
        "intervals": intervals,
        "diagnostics": result["diagnostics"],
        "model_name": model_name
    }
