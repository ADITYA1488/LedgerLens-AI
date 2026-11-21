
AGENT_NAMES = {
    "financial_analyst",
    "forecast_agent",
    "risk_agent",
    "investigation_agent",
    "decision_agent",
    "END",
}


def _is_comprehensive_query(query: str) -> bool:
    q = query.lower()

    comprehensive_phrases = [
        "financial health",
        "overall analysis",
        "comprehensive analysis",
        "complete analysis",
        "full analysis",
        "analyze everything",
        "analyze all",
        "holistic analysis",
    ]

    if any(phrase in q for phrase in comprehensive_phrases):
        return True

    intent_groups = {
        "forecast": [
            "forecast",
            "predict",
            "prediction",
            "future",
            "outlook",
            "project",
        ],
        "risk": [
            "risk",
            "risky",
            "exposure",
            "threat",
            "liquidity",
            "default",
        ],
        "investigation": [
            "why",
            "cause",
            "reason",
            "investigate",
            "root cause",
            "drivers",
        ],
        "decision": [
            "recommend",
            "recommendation",
            "what should",
            "improve",
            "action",
            "solution",
        ],
    }

    detected_intents = sum(
        any(keyword in q for keyword in keywords)
        for keywords in intent_groups.values()
    )

    return detected_intents >= 3


def supervisor_node(state):
    query = state.get("user_query", "").lower().strip()
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 8)

    if iteration_count >= max_iterations:
        return {
            "next_agent": "decision_agent",
            "current_agent": "supervisor",
            "execution_mode": "single",
            "iteration_count": iteration_count + 1,
            "agent_trace": ["supervisor:max_iterations_reached"],
        }

    # Comprehensive financial analysis
    if _is_comprehensive_query(query):
        return {
            "next_agent": "financial_analyst",
            "current_agent": "supervisor",
            "execution_mode": "comprehensive",
            "iteration_count": iteration_count + 1,
            "agent_trace": [
                "supervisor:comprehensive_analysis_detected",
                "supervisor:routed_to:financial_analyst",
            ],
        }

    # Focused query routing
    if any(
        keyword in query
        for keyword in [
            "forecast",
            "predict",
            "prediction",
            "future",
            "next month",
            "next quarter",
            "project",
            "outlook",
        ]
    ):
        next_agent = "forecast_agent"

    elif any(
        keyword in query
        for keyword in [
            "risk",
            "risky",
            "exposure",
            "threat",
            "danger",
            "liquidity",
            "default",
        ]
    ):
        next_agent = "risk_agent"

    elif any(
        keyword in query
        for keyword in [
            "investigate",
            "why",
            "cause",
            "reason",
            "explain",
            "root cause",
            "driver",
            "drivers",
        ]
    ):
        next_agent = "investigation_agent"

    elif any(
        keyword in query
        for keyword in [
            "recommend",
            "recommendation",
            "what should",
            "improve",
            "action",
            "solution",
            "decision",
        ]
    ):
        next_agent = "investigation_agent"

    else:
        next_agent = "financial_analyst"

    if next_agent not in AGENT_NAMES:
        next_agent = "financial_analyst"

    return {
        "next_agent": next_agent,
        "current_agent": "supervisor",
        "execution_mode": "single",
        "iteration_count": iteration_count + 1,
        "agent_trace": [
            f"supervisor:routed_to:{next_agent}",
        ],
    }
