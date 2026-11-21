
import time

from langgraph.graph import StateGraph, START, END

from backend.agents.contracts import validate_agent_output
from backend.agents.state import LedgerLensState
from backend.agents.nodes.supervisor import supervisor_node
from backend.agents.nodes.financial_analyst import financial_analyst_node
from backend.agents.nodes.forecast_agent import forecast_agent_node
from backend.agents.nodes.risk_agent import risk_agent_node
from backend.agents.nodes.investigation_agent import investigation_agent_node
from backend.agents.nodes.decision_agent import decision_agent_node


def route_from_supervisor(state: LedgerLensState) -> str:
    return state.get("next_agent", "financial_analyst")


def is_comprehensive(state: LedgerLensState) -> bool:
    return state.get("execution_mode") == "comprehensive"


def route_after_financial_analyst(state: LedgerLensState) -> str:
    if is_comprehensive(state):
        return "forecast_agent"
    return END


def route_after_forecast(state: LedgerLensState) -> str:
    if is_comprehensive(state):
        return "risk_agent"
    return END


def route_after_risk(state: LedgerLensState) -> str:
    if is_comprehensive(state):
        return "investigation_agent"
    return END


def route_after_investigation(state: LedgerLensState) -> str:
    trace = state.get("agent_trace", [])

    # Never execute downstream agents after investigation failure
    if any(
        "investigation_agent:failed_after_retries" in item
        for item in trace
    ):
        return END

    # Comprehensive workflow always proceeds to final synthesis
    if is_comprehensive(state):
        return "decision_agent"

    query = state.get("user_query", "").lower()

    decision_keywords = [
        "recommend",
        "recommendation",
        "what should",
        "improve",
        "action",
        "solution",
        "decision",
    ]

    if any(keyword in query for keyword in decision_keywords):
        return "decision_agent"

    return END


def enforce_contract(agent_name, node, max_retries=1):
    MAX_AGENT_EXECUTIONS_DEFAULT = 5

    def wrapped(state):
        failures = []
        execution_count = state.get("agent_execution_count", 0)
        execution_budget = state.get(
            "max_agent_executions",
            MAX_AGENT_EXECUTIONS_DEFAULT,
        )

        attempts_used = 0
        total_duration_ms = 0.0

        for attempt in range(max_retries + 1):

            if execution_count + attempts_used >= execution_budget:
                return {
                    "current_agent": agent_name,
                    "agent_execution_count": execution_count + attempts_used,
                    "execution_budget_exceeded": True,
                    "execution_duration_ms": total_duration_ms,
                    "errors": [
                        f"{agent_name} blocked: execution budget "
                        f"({execution_budget}) exhausted."
                    ],
                    "agent_trace": [
                        f"{agent_name}:execution_budget_exceeded",
                        f"{agent_name}:duration:{total_duration_ms:.2f}ms",
                        f"{agent_name}:failed_after_retries",
                    ],
                }

            attempts_used += 1
            attempt_start = time.perf_counter()

            try:
                output = node(state)

            except Exception as exc:
                elapsed_ms = (
                    time.perf_counter() - attempt_start
                ) * 1000

                total_duration_ms += elapsed_ms

                failures.append(
                    f"Attempt {attempt + 1}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

            elapsed_ms = (
                time.perf_counter() - attempt_start
            ) * 1000

            total_duration_ms += elapsed_ms

            errors = validate_agent_output(agent_name, output)

            if not errors:
                output["agent_execution_count"] = (
                    execution_count + attempts_used
                )
                output["execution_budget_exceeded"] = False
                output["execution_duration_ms"] = total_duration_ms

                output["agent_trace"] = output.get(
                    "agent_trace", []
                ) + [
                    f"{agent_name}:duration:{total_duration_ms:.2f}ms"
                ]

                return output

            failures.append(
                f"Attempt {attempt + 1}: " + "; ".join(errors)
            )

        return {
            "current_agent": agent_name,
            "agent_execution_count": execution_count + attempts_used,
            "execution_budget_exceeded": False,
            "execution_duration_ms": total_duration_ms,
            "errors": [
                f"{agent_name} failed after {max_retries + 1} attempts: "
                + " | ".join(failures)
            ],
            "agent_trace": [
                f"{agent_name}:failed_after_retries",
                f"{agent_name}:duration:{total_duration_ms:.2f}ms",
            ],
        }

    return wrapped


def build_graph():
    graph = StateGraph(LedgerLensState)

    graph.add_node("supervisor", supervisor_node)

    graph.add_node(
        "financial_analyst",
        enforce_contract("financial_analyst", financial_analyst_node),
    )

    graph.add_node(
        "forecast_agent",
        enforce_contract("forecast_agent", forecast_agent_node),
    )

    graph.add_node(
        "risk_agent",
        enforce_contract("risk_agent", risk_agent_node),
    )

    graph.add_node(
        "investigation_agent",
        enforce_contract("investigation_agent", investigation_agent_node),
    )

    graph.add_node(
        "decision_agent",
        enforce_contract("decision_agent", decision_agent_node),
    )

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "financial_analyst": "financial_analyst",
            "forecast_agent": "forecast_agent",
            "risk_agent": "risk_agent",
            "investigation_agent": "investigation_agent",
            "decision_agent": "decision_agent",
        },
    )

    # Comprehensive sequential workflow
    graph.add_conditional_edges(
        "financial_analyst",
        route_after_financial_analyst,
        {
            "forecast_agent": "forecast_agent",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "forecast_agent",
        route_after_forecast,
        {
            "risk_agent": "risk_agent",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "risk_agent",
        route_after_risk,
        {
            "investigation_agent": "investigation_agent",
            END: END,
        },
    )

    # Investigation → Decision for comprehensive queries or action requests
    graph.add_conditional_edges(
        "investigation_agent",
        route_after_investigation,
        {
            "decision_agent": "decision_agent",
            END: END,
        },
    )

    graph.add_edge("decision_agent", END)

    return graph.compile()


ledgerlens_graph = build_graph()
