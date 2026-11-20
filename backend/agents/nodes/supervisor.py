from typing import Any

from backend.agents.state import LedgerLensState


AGENT_NAMES = {
    "financial_analyst",
    "forecast_agent",
    "risk_agent",
    "investigation_agent",
    "decision_agent",
    "END",
}


def supervisor_node(state: LedgerLensState) -> dict[str, Any]:
    """
    Deterministic supervisor.

    Routes requests to specialized agents without requiring LLM inference.
    LLM-driven planning will be added later without changing the
    overall graph interface.
    """

    query = state.get("user_query", "").lower().strip()
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 8)

    # Prevent runaway graph execution.
    if iteration >= max_iterations:
        return {
            "next_agent": "decision_agent",
            "current_agent": "supervisor",
            "iteration_count": iteration,
            "agent_trace": ["supervisor:max_iterations_reached"],
        }

    # Determine the initial agent based on query intent.
    if any(word in query for word in [
        "forecast", "predict", "prediction", "future",
        "next month", "next quarter", "project"
    ]):
        target = "forecast_agent"

    elif any(word in query for word in [
        "risk", "risky", "exposure", "threat",
        "danger", "liquidity", "default"
    ]):
        target = "risk_agent"

    elif any(word in query for word in [
        "investigate", "why", "cause", "reason",
        "explain", "root cause", "driver", "drivers"
    ]):
        target = "investigation_agent"

    elif any(word in query for word in [
        "recommend", "recommendation", "what should",
        "action", "improve", "solution", "decision"
    ]):
        target = "investigation_agent"

    else:
        target = "financial_analyst"

    # Validate the destination.
    if target not in AGENT_NAMES:
        target = "financial_analyst"

    return {
        "next_agent": target,
        "current_agent": "supervisor",
        "iteration_count": iteration + 1,
        "agent_trace": [f"supervisor:routed_to:{target}"],
    }