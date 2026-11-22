from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from backend.agents.graph import ledgerlens_graph
import os
from groq import Groq

app = FastAPI(
    title="LedgerLens AI",
    description="Multi-agent financial intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    entity: str = Field("LOG", min_length=3, max_length=3, pattern="^(LOG|MFG|RET)$")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    entity: str = Field("LOG", min_length=3, max_length=3, pattern="^(LOG|MFG|RET)$")

@app.get("/")
def root():
    return {
        "app": "LedgerLens AI",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        financial_context = """
        You are LedgerLens AI, an explainable financial intelligence copilot.

        Current company entity: LOG
        Dataset: DD-WCP-003
        Reporting period: 2026-09-30

        Financial metrics:
        Revenue: $3,093,470.36
        Cost of Sales: $1,625,764.29
        Gross Profit: $1,467,706.07
        Gross Margin: 47.45%
        Supplier Invoices: $2,742,332.35

        Observed trends:
        Revenue declined by 1.33%.
        Cost of sales increased by 5.91%.
        Gross profit declined by 8.27%.
        Supplier invoices represent approximately 88.65% of revenue.

        Risk score: 49/100 (medium risk, heuristic score, NOT probability).

        Detected risks:
        1. Revenue contraction.
        2. Costs growing faster than revenue.
        3. Gross profit deterioration.
        4. Supplier invoice exposure.

        You must:
        - Explain financial concepts in simple but intelligent language.
        - Ground financial answers in the data above.
        - Distinguish facts from possible explanations.
        - Never invent financial metrics.
        - Never claim a possible cause is proven.
        - Give practical investigation steps.
        - If a question is unrelated to company finances, answer briefly.
        - Behave like an intelligent CFO copilot.
        """

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": financial_context
                },
                {
                    "role": "user",
                    "content": request.message
                }
            ],
            max_completion_tokens=700,
            temperature=0.3,
        )

        return {
            "entity": request.entity,
            "reply": response.choices[0].message.content
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Chat service is temporarily unavailable."
        ) from exc

@app.post("/analyze")
def analyze(request: AnalysisRequest):
    try:
        initial_state = {
            "user_query": f"Comprehensive analysis: {request.query.strip()}",
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
        }

        result = ledgerlens_graph.invoke(initial_state)

        findings = {
            "financial_analysis": result.get("analyst_findings", []),
            "forecast": result.get("forecast_findings", []),
            "risks": result.get("risk_findings", []),
            "investigation": result.get("investigation_findings", []),
            "actions": result.get("proposed_actions", []),
        }
        for group in findings.values():
            for item in group:
                if isinstance(item, dict):
                    item.pop("error", None)
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

        return {
            "entity": request.entity,
            "query": request.query,
            "status": (
                "partial" if completed and has_agent_errors
                else "completed" if completed
                else "failed"
            ),
            "current_agent": result.get("current_agent"),
            "findings": findings,
            "trace": result.get("agent_trace", []),
            "errors": ([
                "One or more analysis steps could not be completed."
            ] if result.get("errors") else []) if completed else [
                "Analysis could not be completed with the available data or configuration."
            ],
            "execution_count": result.get("agent_execution_count", 0),
            "execution_duration_ms": result.get("execution_duration_ms", 0),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Analysis service is temporarily unavailable.",
        ) from exc



from datetime import datetime

DEMO_ENTITY_MULTIPLIERS = {
    "LOG": 1.0,
    "MFG": 1.25,
    "RET": 0.82,
}

BASE_METRICS = {
    "revenue": 3093470.36,
    "cost_of_sales": 1625764.29,
    "supplier_invoices": 2742332.35,
}

def get_demo_metrics(entity: str):
    multiplier = DEMO_ENTITY_MULTIPLIERS.get(entity, 1.0)

    revenue = BASE_METRICS["revenue"] * multiplier
    costs = BASE_METRICS["cost_of_sales"] * multiplier
    suppliers = BASE_METRICS["supplier_invoices"] * multiplier
    gross_profit = revenue - costs

    return {
        "revenue": revenue,
        "cost_of_sales": costs,
        "supplier_invoices": suppliers,
        "gross_profit": gross_profit,
        "gross_margin_pct": (gross_profit / revenue * 100) if revenue else 0,
    }

@app.get("/analytics/{entity}")
def analytics(entity: str):
    metrics = get_demo_metrics(entity)

    history = []

    # Synthetic monthly history for demo visualization
    for month in range(12):
        factor = 1 + ((month - 11) * 0.0012)

        history.append({
            "period": f"2025-{month + 1:02d}",
            "revenue": metrics["revenue"] * factor,
            "cost_of_sales": metrics["cost_of_sales"] * (1 + month * 0.005),
            "supplier_invoices": metrics["supplier_invoices"] * factor,
        })

    # Correct ending period
    history[-1]["period"] = "2026-09"

    return {
        "entity": entity,
        "kpis": metrics,
        "history": history,
        "dataset": "DD-WCP-003",
        "dataset_type": "synthetic_demo",
    }

@app.get("/forecast/{entity}/{target}")
def forecast(entity: str, target: str):
    metrics = get_demo_metrics(entity)

    target_map = {
        "Revenue": "revenue",
        "CostOfSales": "cost_of_sales",
        "SupplierInvoices": "supplier_invoices",
    }

    if target not in target_map:
        raise HTTPException(status_code=404, detail="Unknown forecast target")

    value = metrics[target_map[target]]

    return {
        "entity": entity,
        "target": target,
        "model": "Demo Trend Projection",
        "forecast": [
            {
                "period": "2026-10",
                "predicted_value": value * 1.005,
            }
        ],
        "metadata": {
            "forecast_status": "future_forecast",
            "data_freshness": "Synthetic demonstration data",
            "training_end": "2026-09",
            "dataset": "DD-WCP-003",
            "dataset_type": "synthetic_demo",
        },
    }

@app.get("/actions/{entity}")
def actions(entity: str):
    metrics = get_demo_metrics(entity)

    return {
        "entity": entity,
        "actions": [
            {
                "id": f"{entity}-revenue",
                "severity": "medium",
                "status": "open",
                "title": "Investigate revenue contraction",
                "trigger": "Revenue trend indicates a decline requiring review.",
                "financial_value": metrics["revenue"] * 0.0133,
                "financial_value_label": "Revenue change indicator",
                "action": "Review customer churn, order volume, pricing, and sales pipeline.",
                "automation": "Revenue trend monitoring",
            },
            {
                "id": f"{entity}-cost",
                "severity": "high",
                "status": "open",
                "title": "Review cost growth",
                "trigger": "Costs are increasing faster than revenue in the demo scenario.",
                "financial_value": metrics["cost_of_sales"] * 0.0591,
                "financial_value_label": "Cost growth indicator",
                "action": "Investigate procurement prices, product mix, and operating costs.",
                "automation": "Cost variance monitoring",
            },
            {
                "id": f"{entity}-supplier",
                "severity": "medium",
                "status": "open",
                "title": "Monitor supplier exposure",
                "trigger": "Supplier invoices are high relative to revenue.",
                "financial_value": metrics["supplier_invoices"],
                "financial_value_label": "Supplier invoice volume",
                "action": "Review supplier concentration, payment terms, and upcoming obligations.",
                "automation": "Supplier exposure monitoring",
            },
        ],
    }
