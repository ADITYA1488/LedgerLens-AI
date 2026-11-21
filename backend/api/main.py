from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.agents.graph import ledgerlens_graph


app = FastAPI(
    title="LedgerLens AI",
    description="Multi-agent financial intelligence API",
    version="0.1.0",
)


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3)
    entity: str = "LOG"


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


@app.post("/analyze")
def analyze(request: AnalysisRequest):
    try:
        initial_state = {
            "user_query": request.query,
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

        return {
            "entity": request.entity,
            "query": request.query,
            "current_agent": result.get("current_agent"),
            "findings": {
                "financial_analysis": result.get("analyst_findings", []),
                "forecast": result.get("forecast_findings", []),
                "risks": result.get("risk_findings", []),
                "investigation": result.get("investigation_findings", []),
                "actions": result.get("proposed_actions", []),
            },
            "trace": result.get("agent_trace", []),
            "errors": result.get("errors", []),
            "execution_count": result.get("agent_execution_count", 0),
            "execution_duration_ms": result.get("execution_duration_ms", 0),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(exc)}",
        )