
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException

from forecasting import forecast_financial_series
from forecasting_schema import (
    ForecastPoint,
    EvaluationMetrics,
    ForecastMetadata,
    ForecastResponse
)

app = FastAPI(
    title="LedgerLens AI API",
    description="Financial forecasting and working-capital intelligence",
    version="0.2.0"
)

DATA_ROOT = Path(
    "/kaggle/input/datasets/adityashrinet/"
    "ledgerlens-msme-working-capital/"
)

SELECTION_FILE = Path(
    "/kaggle/working/ledgerlens_experiments/"
    "selected_forecasting_models.csv"
)

TARGETS = {
    "revenue": "Revenue",
    "costofsales": "CostOfSales",
    "supplierinvoices": "SupplierInvoices"
}

MODEL_MAP = {
    "Holt-Winters": "holt_winters",
    "Moving Average": "moving_average_3"
}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "LedgerLens AI",
        "version": "0.2.0"
    }


@app.get(
    "/forecast/{entity}/{target}",
    response_model=ForecastResponse
)
def get_forecast(entity: str, target: str):

    entity = entity.upper()
    target_key = target.lower()

    if entity not in ["LOG", "MFG", "RET"]:
        raise HTTPException(400, "Unsupported entity.")

    if target_key not in TARGETS:
        raise HTTPException(400, "Unsupported financial target.")

    if not DATA_ROOT.exists() or not SELECTION_FILE.exists():
        raise HTTPException(
            500,
            "Dataset or model selection artifact is unavailable."
        )

    target_column = TARGETS[target_key]

    try:
        selection = pd.read_csv(SELECTION_FILE)

        selected = selection[
            (selection["Entity"] == entity) &
            (selection["Target"] == target_column)
        ]

        if len(selected) != 1:
            raise ValueError("Model selection not found or ambiguous.")

        selected_model = selected.iloc[0]["Model"]
        method = MODEL_MAP[selected_model]

        files = list(
            DATA_ROOT.rglob("DD-WCP-003_FactMonthlyPL.csv")
        )

        if not files:
            raise FileNotFoundError("Monthly P&L dataset not found.")

        pl = pd.read_csv(files[0])
        pl["MonthEnd"] = pd.to_datetime(pl["MonthEnd"])

        series = (
            pl[pl["EntityCode"] == entity]
            .set_index("MonthEnd")[target_column]
            .sort_index()
            .asfreq("ME")
            .astype(float)
        )

        result = forecast_financial_series(
            series=series,
            horizon=1,
            method=method
        )

        forecast_points = [
            ForecastPoint(
                period=str(date.date()),
                predicted_value=float(value)
            )
            for date, value in result["forecast"].items()
        ]

        return ForecastResponse(
            entity=entity,
            target=target_column,
            model=method,
            forecast=forecast_points,
            evaluation=EvaluationMetrics(),
            metadata=ForecastMetadata(
                dataset="DD-WCP-003",
                dataset_type="synthetic",
                currency="USD",
                training_end=str(series.index[-1].date())
            )
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
