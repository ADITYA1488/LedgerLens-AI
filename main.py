from functools import lru_cache
from action_engine import generate_financial_actions
from pathlib import Path
from datetime import datetime
import os
import io
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from action_store import (
    initialize_action_store,
    upsert_generated_actions,
    get_actions,
    update_action_status,
    get_action_history,
)
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
        str(PROJECT_ROOT / "data" / "dataset")
    )
).resolve()

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


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    entity: str = Field("LOG", min_length=3, max_length=3, pattern="^(LOG|MFG|RET)$")

app = FastAPI(
    title="LedgerLens AI API",
    description="Financial forecasting and working-capital intelligence",
    version="0.3.0"
)
@app.on_event("startup")
def startup_event():
    initialize_action_store()
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
    """Validate and safely activate a monthly financial CSV."""
    import os
    import tempfile
    import shutil
    from datetime import datetime

    raw = await request.body()

    if not raw:
        raise HTTPException(400, "Upload body is empty.")

    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "CSV exceeds the 10 MB upload limit.")

    required = {
        "EntityCode",
        "MonthEnd",
        "Revenue",
        "CostOfSales",
        "SupplierInvoices",
    }
    numeric_columns = ["Revenue", "CostOfSales", "SupplierInvoices"]

    try:
        frame = pd.read_csv(io.BytesIO(raw))

        missing_columns = required.difference(frame.columns)
        if missing_columns:
            raise HTTPException(
                400,
                f"Missing required columns: {sorted(missing_columns)}"
            )

        if frame.empty:
            raise HTTPException(400, "CSV contains no records.")

        # Normalize entity identifiers.
        frame["EntityCode"] = (
            frame["EntityCode"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        if frame["EntityCode"].isna().any() or (
            frame["EntityCode"] == ""
        ).any():
            raise HTTPException(400, "EntityCode contains empty values.")

        unsupported = set(frame["EntityCode"].unique()) - SUPPORTED_ENTITIES
        if unsupported:
            raise HTTPException(
                400,
                f"Unsupported entities: {sorted(unsupported)}"
            )

        # Validate dates.
        frame["MonthEnd"] = pd.to_datetime(
            frame["MonthEnd"],
            errors="coerce"
        )

        if frame["MonthEnd"].isna().any():
            raise HTTPException(400, "CSV contains invalid dates.")

        if not frame["MonthEnd"].dt.is_month_end.all():
            raise HTTPException(
                400,
                "MonthEnd must contain month-end dates."
            )

        # Validate financial values.
        for column in numeric_columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce"
            )

            if frame[column].isna().any():
                raise HTTPException(
                    400,
                    f"{column} contains missing or invalid numeric values."
                )

            if not np.isfinite(frame[column]).all():
                raise HTTPException(
                    400,
                    f"{column} contains infinite values."
                )

        # Prevent ambiguous duplicate records.
        duplicates = frame.duplicated(
            subset=["EntityCode", "MonthEnd"],
            keep=False
        )

        if duplicates.any():
            duplicate_rows = frame.loc[
                duplicates, ["EntityCode", "MonthEnd"]
            ]
            raise HTTPException(
                400,
                "Duplicate entity-month records detected: "
                + duplicate_rows.to_string(index=False)
            )

        # Validate monthly continuity for each entity.
        missing_periods = []

        for entity, group in frame.groupby("EntityCode"):
            dates = group["MonthEnd"].sort_values()

            expected = pd.date_range(
                start=dates.min(),
                end=dates.max(),
                freq="ME"
            )

            missing = expected.difference(dates)

            if len(missing):
                missing_periods.append(
                    f"{entity}: "
                    + ", ".join(missing.strftime("%Y-%m"))
                )

        if missing_periods:
            raise HTTPException(
                400,
                "Missing monthly periods detected. "
                + " | ".join(missing_periods)
            )

        # Sort and prepare validated dataset.
        frame = frame.sort_values(
            ["EntityCode", "MonthEnd"]
        ).reset_index(drop=True)

        DATA_ROOT.mkdir(parents=True, exist_ok=True)

        destination = DATA_ROOT / "DD-WCP-003_FactMonthlyPL.csv"

        # Write to a temporary file in the same directory.
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".tmp",
                prefix="ledgerlens_",
                dir=DATA_ROOT,
                delete=False,
                encoding="utf-8",
                newline=""
            ) as temp_file:
                temp_path = temp_file.name
                frame.to_csv(temp_file, index=False)

            # Preserve the currently active dataset.
            backup_path = None

            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = destination.with_name(
                    f"{destination.stem}_{timestamp}.backup.csv"
                )
                shutil.copy2(destination, backup_path)

            # Atomic activation.
            os.replace(temp_path, destination)
            temp_path = None

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        # Clear cache only after successful activation.
        load_monthly_data.cache_clear()

        return {
            "status": "uploaded",
            "filename": destination.name,
            "rows": int(len(frame)),
            "entities": sorted(frame["EntityCode"].unique().tolist()),
            "latest_period": str(frame["MonthEnd"].max().date()),
            "dataset_configured": True,
            "backup_created": backup_path is not None,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            400,
            f"CSV validation failed: {str(exc)}"
        )


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "LedgerLens AI",
        "version": "0.3.0",
        "dataset_configured": DATA_ROOT.exists(),
        "selection_configured": SELECTION_FILE.exists()
    }


@app.post("/analyze")
def analyze(request: AnalysisRequest):
    """Run a full, evidence-based analysis through the existing agent graph."""
    try:
        query = request.query.strip()
        if len(query) < 3:
            raise HTTPException(422, "Query must contain at least 3 non-whitespace characters.")

        # Agent nodes import analytics helpers from main, so defer this import
        # until the application module has finished initializing.
        from backend.agents.graph import ledgerlens_graph

        result = ledgerlens_graph.invoke({
            "user_query": f"Comprehensive analysis: {query}",
            "entity": request.entity,
            "agent_trace": [],
            "errors": [],
            "evidence": [],
            "analyst_findings": [],
            "forecast_findings": [],
            "risk_findings": [],
            "investigation_findings": [],
            "proposed_actions": [],
            "agent_execution_count": 0,
            "max_agent_executions": 5,
            "execution_budget_exceeded": False,
        })

        findings = {
            "financial_analysis": result.get("analyst_findings", []),
            "forecast": result.get("forecast_findings", []),
            "risks": result.get("risk_findings", []),
            "investigation": result.get("investigation_findings", []),
            "actions": result.get("proposed_actions", []),
        }
        completed = any(
            item.get("status") == "success"
            for group in findings.values()
            for item in group
            if isinstance(item, dict)
        )
        has_agent_errors = bool(result.get("errors")) or any(
            item.get("status") == "error"
            for group in findings.values()
            for item in group
            if isinstance(item, dict)
        )
        for group in findings.values():
            for item in group:
                if isinstance(item, dict):
                    # Agent exception strings can contain provider details or local paths.
                    item.pop("error", None)
        return {
            "entity": request.entity,
            "query": query,
            "status": (
                "partial" if completed and has_agent_errors
                else "completed" if completed
                else "failed"
            ),
            "findings": findings,
            "trace": result.get("agent_trace", []),
            "errors": ([
                "One or more analysis steps could not be completed."
            ] if has_agent_errors else []) if completed else [
                "Analysis could not be completed with the available data or configuration."
            ],
            "execution_count": result.get("agent_execution_count", 0),
            "execution_duration_ms": result.get("execution_duration_ms", 0),
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Keep internal paths, provider errors, and configuration details out of API responses.
        raise HTTPException(500, "Analysis service is temporarily unavailable.") from exc


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

        # Forecast period classification
        forecast_date = datetime.strptime(
            forecast_points[0].period, "%Y-%m-%d"
        )

        forecast_month = (forecast_date.year, forecast_date.month)
        current_month = (datetime.now().year, datetime.now().month)

        if forecast_month < current_month:
            forecast_status = "historical_forecast"
        elif forecast_month == current_month:
            forecast_status = "current_period_estimate"
        else:
            forecast_status = "future_forecast"

        # Underlying data freshness
        training_date = datetime.strptime(
            str(series.index[-1].date()), "%Y-%m-%d"
        )

        months_behind = (
                (datetime.now().year - training_date.year) * 12
                + datetime.now().month - training_date.month
        )

        data_freshness = (
            "current"
            if months_behind <= 0
            else f"{months_behind} months behind"
        )

        return ForecastResponse(
            entity=entity,
            target=target_column,
            model=method,
            forecast=forecast_points,
            evaluation=EvaluationMetrics(),
            metadata=ForecastMetadata(
                dataset="DD-WCP-003",
                dataset_type="synthetic",
                currency="INR",
                training_end=str(series.index[-1].date()),
                forecast_status=forecast_status,
                data_freshness=data_freshness,
            ),
        )

    except FileNotFoundError as exc:
        raise HTTPException(503, "Required financial data is unavailable.") from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(500, "Forecast service is temporarily unavailable.") from exc



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
        raise HTTPException(
            status_code=503,
            detail="Required financial data is unavailable."
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Analytics service is temporarily unavailable."
        ) from exc


@app.get("/actions/{entity}")
def get_financial_actions(entity: str):
    entity = entity.upper()

    if entity not in SUPPORTED_ENTITIES:
        raise HTTPException(400, "Unsupported entity.")

    try:
        data = load_monthly_data()

        # Generate current financial actions
        generated = generate_financial_actions(data, entity)

        # Persist generated actions
        upsert_generated_actions(entity, generated)

        # Retrieve persistent action records
        actions = get_actions(entity)

        # Sort by active status, then severity
        status_order = {
            "open": 0,
            "in_progress": 1,
            "completed": 2,
            "dismissed": 3
        }

        severity_order = {
            "high": 0,
            "medium": 1,
            "low": 2
        }

        actions.sort(
            key=lambda action: (
                status_order.get(action["status"], 4),
                severity_order.get(action["severity"], 3)
            )
        )

        active_actions = [
            action for action in actions
            if action["status"] not in {"completed", "dismissed"}
        ]

        return {
            "entity": entity,
            "generated_at": datetime.utcnow().isoformat(),
            "total_actions": len(actions),
            "active_actions": len(active_actions),
            "high_priority": sum(
                1 for action in active_actions
                if action["severity"] == "high"
            ),
            "actions": actions
        }

    except FileNotFoundError as exc:
        raise HTTPException(503, "Required financial data is unavailable.") from exc

    except Exception as exc:
        raise HTTPException(500, "Action service is temporarily unavailable.") from exc

class ActionStatusUpdate(BaseModel):
    status: str
    notes: str = ""


@app.patch("/actions/{action_id}/status")
def change_action_status(action_id: str, payload: ActionStatusUpdate):
    try:
        result = update_action_status(
            action_id=action_id,
            new_status=payload.status,
            notes=payload.notes
        )

        if result is None:
            raise HTTPException(404, "Action not found.")

        return {
            "success": True,
            "message": "Action status updated.",
            "action": result
        }

    except ValueError as exc:
        raise HTTPException(400, str(exc))

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(500, "Action update failed.") from exc

@app.get("/actions/{action_id}/history")
def get_action_history_endpoint(action_id: str):
    try:
        history = get_action_history(action_id)

        return {
            "action_id": action_id,
            "total_events": len(history),
            "history": history
        }

    except Exception as exc:
        raise HTTPException(500, "Action history is temporarily unavailable.") from exc
