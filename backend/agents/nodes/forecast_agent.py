from typing import Any

from backend.agents.state import LedgerLensState
from backend.agents.schemas import FinancialAnalysis
from backend.agents.nodes.financial_reasoning import deterministic_analysis
from main import get_forecast


TARGET_MAP = {
    "revenue": "revenue",
    "cost of sales": "costofsales",
    "costofsales": "costofsales",
    "supplier invoices": "supplierinvoices",
    "supplierinvoices": "supplierinvoices",
}


def detect_target(query: str) -> str:
    q = query.lower()

    if any(x in q for x in ["supplier", "invoice", "payable"]):
        return "supplierinvoices"

    if any(x in q for x in ["cost", "expense", "cogs"]):
        return "costofsales"

    return "revenue"


def forecast_agent_node(state: LedgerLensState) -> dict[str, Any]:
    entity = state.get("entity", "LOG").upper()
    query = state.get("user_query", "")
    target = detect_target(query)

    try:
        response = get_forecast(entity, target)

        if hasattr(response, "model_dump"):
            forecast_data = response.model_dump()
        else:
            forecast_data = response

        forecast_values = forecast_data.get("forecast", [])
        metadata = forecast_data.get("metadata", {})

        if not forecast_values:
            raise ValueError("Forecast engine returned no forecast values.")

        latest_forecast = forecast_values[-1]
        predicted_value = float(latest_forecast["predicted_value"])
        forecast_period = latest_forecast["period"]

        findings = {
            "agent": "forecast_agent",
            "entity": entity,
            "query": query,
            "status": "success",
            "target": forecast_data.get("target", target),
            "model": forecast_data.get("model"),
            "forecast": forecast_values,
            "predicted_value": predicted_value,
            "forecast_period": forecast_period,
            "metadata": metadata,
            "interpretation": (
                f"The selected forecasting model predicts "
                f"{forecast_data.get('target', target)} of "
                f"{predicted_value:,.2f} for {forecast_period}."
            ),
            "reasoning_mode": "deterministic_forecast",
        }

        evidence = [
            {
                "source": "existing_forecasting_engine",
                "entity": entity,
                "target": forecast_data.get("target", target),
                "model": forecast_data.get("model"),
                "period": forecast_period,
                "predicted_value": predicted_value,
            }
        ]

        return {
            "current_agent": "forecast_agent",
            "forecast_findings": [findings],
            "evidence": evidence,
            "agent_trace": [
                "forecast_agent:forecast_generated",
                "forecast_agent:evidence_constructed",

            ],
        }

    except Exception as exc:
        return {
            "current_agent": "forecast_agent",
            "forecast_findings": [{
                "agent": "forecast_agent",
                "entity": entity,
                "query": query,
                "status": "error",
                "error": str(exc),

            }],
            "errors": [f"forecast_agent: {str(exc)}"],
            "agent_trace": ["forecast_agent:execution_failed"],
        }