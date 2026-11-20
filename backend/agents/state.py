from typing import Annotated, Any, TypedDict
import operator


class LedgerLensState(TypedDict, total=False):
    # User request
    user_query: str
    entity: str

    # Supervisor routing
    next_agent: str
    current_agent: str
    execution_mode: str

    # Shared evidence
    evidence: Annotated[list[dict[str, Any]], operator.add]

    # Agent findings
    analyst_findings: Annotated[list[dict[str, Any]], operator.add]
    forecast_findings: Annotated[list[dict[str, Any]], operator.add]
    risk_findings: Annotated[list[dict[str, Any]], operator.add]
    investigation_findings: Annotated[list[dict[str, Any]], operator.add]

    # Decision/action proposals
    proposed_actions: Annotated[list[dict[str, Any]], operator.add]

    # Execution control
    iteration_count: int
    max_iterations: int
    agent_execution_count: int
    max_agent_executions: int
    execution_budget_exceeded: bool

    # Observability
    agent_trace: Annotated[list[str], operator.add]
    execution_duration_ms: float

    # Errors
    errors: Annotated[list[str], operator.add]

    # Final output
    final_response: str
    is_complete: bool