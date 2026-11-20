from typing import Any


REQUIRED_STATE_KEYS = [
    "user_query",
    "entity",
    "current_agent",
    "agent_trace",
    "errors",
]


AGENT_OUTPUT_REQUIREMENTS = {
    "financial_analyst": ["analyst_findings"],
    "forecast_agent": ["forecast_findings"],
    "risk_agent": ["risk_findings"],
    "investigation_agent": ["investigation_findings"],
    "decision_agent": ["proposed_actions"],
}


def validate_state(state: dict[str, Any]) -> list[str]:
    errors = []

    for key in REQUIRED_STATE_KEYS:
        if key not in state:
            errors.append(f"Missing state key: {key}")

    for key in [
        "evidence",
        "analyst_findings",
        "forecast_findings",
        "risk_findings",
        "investigation_findings",
        "proposed_actions",
        "agent_trace",
        "errors",
    ]:
        if key in state and not isinstance(state[key], list):
            errors.append(f"{key} must be a list")

    return errors


def validate_agent_output(
    agent_name: str,
    output: dict[str, Any],
) -> list[str]:
    errors = []

    if not isinstance(output, dict):
        return ["Agent output must be a dictionary"]

    if output.get("current_agent") != agent_name:
        errors.append(
            f"Agent identity mismatch: expected {agent_name}"
        )

    required_fields = AGENT_OUTPUT_REQUIREMENTS.get(agent_name, [])

    for field in required_fields:
        if field not in output:
            errors.append(f"{agent_name} missing output field: {field}")

        elif not isinstance(output[field], list):
            errors.append(f"{field} must be a list")

    if "agent_trace" in output and not isinstance(output["agent_trace"], list):
        errors.append("agent_trace must be a list")

    if "errors" in output and not isinstance(output["errors"], list):
        errors.append("errors must be a list")

    return errors