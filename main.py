from functools import lru_cache
from pathlib import Path
import os

import pandas as pd
from fastapi import FastAPI, HTTPException
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



WORKING_CAPITAL_FILE = Path(
    os.getenv(
        "LEDGERLENS_WC_FILE",
        str(PROJECT_ROOT / "data" / "working_capital_monthly.csv")
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
    allow_methods=["GET", "OPTIONS"],
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


@lru_cache(maxsize=1)
def load_working_capital_data():
    if not WORKING_CAPITAL_FILE.exists():
        raise FileNotFoundError(
            f"Working capital CSV not found: {WORKING_CAPITAL_FILE}"
        )

    data = pd.read_csv(WORKING_CAPITAL_FILE)

    required = {
        "EntityCode", "period", "dso_days",
        "card_receivable_days_proxy", "dpo_days",
        "dio_days", "ccc_days", "receivables_metric",
        "ccc_status", "data_provenance"
    }

    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            f"Working capital CSV missing columns: {sorted(missing)}"
        )

    data["EntityCode"] = data["EntityCode"].astype(str).str.upper()
    data["period"] = pd.to_datetime(data["period"], errors="coerce")

    if data["period"].isna().any():
        raise ValueError("Invalid period values in working capital CSV.")

    if data.duplicated(["EntityCode", "period"]).any():
        raise ValueError("Duplicate entity-month rows in working capital CSV.")

    return data.sort_values(["EntityCode", "period"]).copy()


def _safe_number(value):
    if pd.isna(value):
        return None
    return float(value)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "LedgerLens AI",
        "version": "0.3.0",
        "dataset_configured": DATA_ROOT.exists(),
        "selection_configured": SELECTION_FILE.exists(),
        "working_capital_configured": WORKING_CAPITAL_FILE.exists()
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



@app.get("/working-capital/{entity}")
def get_working_capital(entity: str):
    entity = entity.upper()

    if entity not in SUPPORTED_ENTITIES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported entity. Use LOG, MFG or RET."
        )

    try:
        data = load_working_capital_data()
        entity_data = (
            data[data["EntityCode"] == entity]
            .sort_values("period")
            .copy()
        )

        if entity_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No working-capital data found for {entity}."
            )

        latest = entity_data.iloc[-1]
        history = entity_data.tail(12)

        metric_columns = [
            "dso_days",
            "card_receivable_days_proxy",
            "dpo_days",
            "dio_days",
            "ccc_days"
        ]

        metric_labels = {
            "dso_days": "Days sales outstanding",
            "card_receivable_days_proxy": "Card receivable settlement days proxy",
            "dpo_days": "Days payables outstanding",
            "dio_days": "Days inventory outstanding",
            "ccc_days": "Cash conversion cycle"
        }

        metrics = {
            column: {
                "value": _safe_number(latest[column]),
                "label": metric_labels[column]
            }
            for column in metric_columns
        }

        history_records = []
        for _, row in history.iterrows():
            record = {
                "period": row["period"].date().isoformat()
            }
            record.update({
                column: _safe_number(row[column])
                for column in metric_columns
            })
            history_records.append(record)

        return {
            "entity": entity,
            "dataset": "DD-WCP-003",
            "dataset_type": "synthetic",
            "currency": "USD",
            "data_provenance": str(latest["data_provenance"]),
            "latest_period": latest["period"].date().isoformat(),
            "receivables_metric": str(latest["receivables_metric"]),
            "ccc_status": str(latest["ccc_status"]),
            "metrics": metrics,
            "history": history_records,
            "metric_notes": {
                "LOG": "Trade DSO and DPO are available. DIO and CCC are unavailable because inventory data is missing.",
                "MFG": "Trade DSO, DPO, DIO and CCC are available.",
                "RET": "Card receivable settlement days are a proxy, not conventional trade DSO. Conventional CCC is unavailable."
            }[entity]
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
