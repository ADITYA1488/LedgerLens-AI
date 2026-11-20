from typing import Any

from backend.agents.state import LedgerLensState
from backend.agents.nodes.financial_context import build_financial_context
from backend.agents.nodes.financial_reasoning import analyze_financial_evidence


def financial_analyst_node(state: LedgerLensState) -> dict[str, Any]:
    entity = state.get("entity", "LOG").upper()
    query = state.get("user_query", "")

    try:
        from main import get_entity_analytics

        # Step 1: Retrieve deterministic financial analytics
        analytics = get_entity_analytics(entity)

        # Step 2: Construct evidence context
        context = build_financial_context(analytics)

        # Step 3: Perform structured financial reasoning
        analysis = analyze_financial_evidence(
            context,
            use_llm=True,
        )

        analysis_dict = analysis.model_dump()

        # Step 4: Store results in shared graph state
        finding = {
            "agent": "financial_analyst",
            "entity": entity,
            "query": query,
            "status": "success",
            "metrics": context.get("current_financials", {}),
            "context": context,
            "analysis": analysis_dict,
            "reasoning_mode": (
                "llm"
                if analysis.analysis_status == "complete"
                else "fallback"
            ),
        }

        evidence = {
            "source": "existing_analytics_engine",
            "entity": entity,
            "data": context,
        }

        return {
            "current_agent": "financial_analyst",
            "analyst_findings": [finding],
            "evidence": [evidence],
            "agent_trace": [
                "financial_analyst:analytics_retrieved",
                "financial_analyst:context_constructed",
                "financial_analyst:reasoning_completed",
            ],
        }

    except Exception as exc:
        error_message = f"Financial Analyst failed: {str(exc)}"

        return {
            "current_agent": "financial_analyst",
            "errors": [error_message],
            "analyst_findings": [{
                "agent": "financial_analyst",
                "entity": entity,
                "status": "error",
                "error": error_message,
            }],
            "agent_trace": [
                "financial_analyst:failed",
            ],
        }
