from functools import lru_cache
from pathlib import Path
import os
import io

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from forecasting import forecast_financial_series
from forecasting_schema import (
    ForecastPoint,
    EvaluationMetrics,
    ForecastMetadata,
    ForecastResponse
)

PROJECT_ROOT = Path(
    os.getenv("LEDGERLENS_PROJECT_ROOT", Path.cwd())
).resolve()

DATA_ROOT = Path(
    os.getenv(
        "LEDGERLENS_DATA_DIR",
        "/kaggle/input/datasets/adityashrinet/"
        "ledgerlens-msme-working-capital/"
    )
)

SELECTION_FILE = Path(
    os.getenv(
        "LEDGERLENS_SELECTION_FILE",
        str(PROJECT_ROOT / "experiments" / "selected_forecasting_models.csv")
    )
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

SUPPORTED_ENTITIES = {"LOG", "MFG", "RET"}

app = FastAPI(
    title="LedgerLens AI API",
    description="Financial forecasting and working-capital intelligence",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


@lru_cache(maxsize=1)
def load_monthly_data():
    if not DATA_ROOT.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {DATA_ROOT}"
        )

    files = list(
        DATA_ROOT.rglob("DD-WCP-003_FactMonthlyPL.csv")
    )

    if not files:
        raise FileNotFoundError(
            "DD-WCP-003_FactMonthlyPL.csv not found."
        )

    pl = pd.read_csv(files[0])
    pl["MonthEnd"] = pd.to_datetime(pl["MonthEnd"])

    return pl


@lru_cache(maxsize=1)
def load_model_selection():
    if not SELECTION_FILE.exists():
        raise FileNotFoundError(
            f"Model selection file not found: {SELECTION_FILE}"
        )

    selection = pd.read_csv(SELECTION_FILE)

    required = {"Entity", "Target", "Model"}

    if not required.issubset(selection.columns):
        raise ValueError(
            f"Model selection file must contain {required}."
        )

    return selection


@app.post("/data/upload")
async def upload_monthly_dataset(request: Request):
    """Upload a validated monthly P&L CSV and activate it for forecasting."""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Upload body is empty.")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "CSV exceeds the 10 MB upload limit.")
    try:
        frame = pd.read_csv(io.BytesIO(raw))
        required = {"EntityCode", "MonthEnd", "Revenue", "CostOfSales", "SupplierInvoices"}
        missing = required.difference(frame.columns)
        if missing:
            raise HTTPException(400, f"CSV missing required columns: {sorted(missing)}")
        frame["MonthEnd"] = pd.to_datetime(frame["MonthEnd"], errors="raise")
        if frame.empty or frame["EntityCode"].isna().any():
            raise HTTPException(400, "CSV has no rows or contains missing entity codes.")
        if not set(frame["EntityCode"].astype(str).str.upper()).issubset(SUPPORTED_ENTITIES):
            raise HTTPException(400, "CSV contains unsupported entity codes. Expected LOG, MFG, RET.")
        for col in ["Revenue", "CostOfSales", "SupplierInvoices"]:
            frame[col] = pd.to_numeric(frame[col], errors="raise")
        frame = frame.sort_values(["EntityCode", "MonthEnd"])
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        destination = DATA_ROOT / "DD-WCP-003_FactMonthlyPL.csv"
        frame.to_csv(destination, index=False)
        load_monthly_data.cache_clear()
        return {
            "status": "uploaded",
            "filename": destination.name,
            "rows": int(len(frame)),
            "entities": sorted(frame["EntityCode"].astype(str).str.upper().unique().tolist()),
            "latest_period": str(frame["MonthEnd"].max().date()),
            "dataset_configured": True
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"CSV validation failed: {exc}")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "LedgerLens AI",
        "version": "0.3.0",
        "dataset_configured": DATA_ROOT.exists(),
        "selection_configured": SELECTION_FILE.exists()
    }


@app.get(
    "/forecast/{entity}/{target}",
    response_model=ForecastResponse
)
def get_forecast(entity: str, target: str):

    entity = entity.upper()
    target_key = target.lower()

    if entity not in SUPPORTED_ENTITIES:
        raise HTTPException(400, "Unsupported entity.")

    if target_key not in TARGETS:
        raise HTTPException(400, "Unsupported financial target.")

    try:
        pl = load_monthly_data()
        selection = load_model_selection()

        target_column = TARGETS[target_key]

        selected = selection[
            (selection["Entity"] == entity) &
            (selection["Target"] == target_column)
        ]

        if len(selected) != 1:
            raise ValueError(
                f"Expected one model selection for {entity}/{target_column}."
            )

        selected_model = selected.iloc[0]["Model"]

        if selected_model not in MODEL_MAP:
            raise ValueError(
                f"Unsupported selected model: {selected_model}"
            )

        method = MODEL_MAP[selected_model]

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

    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc))

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(500, str(exc))



@app.get("/analytics/{entity}")
def get_entity_analytics(entity: str):

    entity = entity.upper()

    if entity not in SUPPORTED_ENTITIES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported entity."
        )

    try:
        pl = load_monthly_data()

        entity_data = (
            pl[pl["EntityCode"] == entity]
            .sort_values("MonthEnd")
            .copy()
        )

        if entity_data.empty:
            raise ValueError(f"No data found for {entity}.")

        entity_data["GrossProfit"] = (
            entity_data["Revenue"] - entity_data["CostOfSales"]
        )

        entity_data["GrossMarginPct"] = (
            entity_data["GrossProfit"] /
            entity_data["Revenue"].replace(0, float("nan"))
        ) * 100

        latest = entity_data.iloc[-1]

        history = entity_data.tail(12)

        return {
            "entity": entity,
            "dataset": "DD-WCP-003",
            "dataset_type": "synthetic",
            "currency": "USD",
            "latest_period": str(latest["MonthEnd"].date()),
            "kpis": {
                "revenue": float(latest["Revenue"]),
                "cost_of_sales": float(latest["CostOfSales"]),
                "supplier_invoices": float(latest["SupplierInvoices"]),
                "gross_profit": float(latest["GrossProfit"]),
                "gross_margin_pct": (
                    None if pd.isna(latest["GrossMarginPct"])
                    else float(latest["GrossMarginPct"])
                )
            },
            "history": [
                {
                    "period": str(row["MonthEnd"].date()),
                    "revenue": float(row["Revenue"]),
                    "cost_of_sales": float(row["CostOfSales"]),
                    "supplier_invoices": float(row["SupplierInvoices"]),
                    "gross_profit": float(row["GrossProfit"]),
                    "gross_margin_pct": (
                        None if pd.isna(row["GrossMarginPct"])
                        else float(row["GrossMarginPct"])
                    )
                }
                for _, row in history.iterrows()
            ]
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
