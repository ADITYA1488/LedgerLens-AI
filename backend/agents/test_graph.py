from backend.agents.graph import ledgerlens_graph
from backend.agents.nodes.financial_analyst import financial_analyst_node
from backend.agents.nodes.financial_context import build_financial_context
from backend.agents.nodes.financial_reasoning import deterministic_analysis
from main import get_entity_analytics

TEST_CASES = [
    ("What is our revenue?", "financial_analyst"),
    ("Forecast next month revenue", "forecast_agent"),
    ("What are our financial risks?", "risk_agent"),
    ("Why did our costs increase?", "investigation_agent"),
    ("What should we do to improve profitability?", "decision_agent"),
]


def make_initial_state(query: str) -> dict:
    return {
        "user_query": query,
        "entity": "LOG",
        "next_agent": "",
        "current_agent": "",
        "execution_mode": "test",
        "evidence": [],
        "analyst_findings": [],
        "forecast_findings": [],
        "risk_findings": [],
        "investigation_findings": [],
        "proposed_actions": [],
        "iteration_count": 0,
        "max_iterations": 8,
        "agent_trace": [],
        "errors": [],
        "final_response": "",
        "is_complete": False,
    }


def test_agent_routing():
    print("\n=== Agent Routing Tests ===")

    passed = 0

    for query, expected_agent in TEST_CASES:
        result = ledgerlens_graph.invoke(make_initial_state(query))
        actual_agent = result.get("current_agent")

        success = actual_agent == expected_agent

        print(f"{'PASS' if success else 'FAIL'} | {query} | {actual_agent}")

        if success:
            passed += 1

    assert passed == len(TEST_CASES)
    print(f"Routing: {passed}/{len(TEST_CASES)} PASS")


def test_financial_context():
    print("\n=== Financial Context Tests ===")

    analytics = get_entity_analytics("LOG")
    context = build_financial_context(analytics)

    assert context["entity"] == "LOG"
    assert context["current_financials"]["revenue"] > 0
    assert context["current_financials"]["gross_profit"] > 0
    assert context["current_financials"]["gross_margin_pct"] is not None
    assert context["history_months_available"] >= 2

    ratios = context["financial_ratios"]

    assert ratios["cost_of_sales_to_revenue_pct"] is not None
    assert ratios["supplier_invoices_to_revenue_pct"] is not None

    comparison = context["historical_comparison"]

    assert comparison
    assert comparison["revenue_change_pct"] is not None
    assert comparison["cost_of_sales_change_pct"] is not None

    print("Entity:", context["entity"])
    print("Revenue:", context["current_financials"]["revenue"])
    print("Gross margin:", context["current_financials"]["gross_margin_pct"])
    print("History months:", context["history_months_available"])
    print("Context validation: PASS")


def test_deterministic_intelligence():
    print("\n=== Financial Intelligence Validation ===")

    context = build_financial_context(get_entity_analytics("LOG"))
    analysis = deterministic_analysis(context)

    assert analysis.entity == "LOG"
    assert analysis.reporting_period
    assert analysis.executive_summary

    assert isinstance(analysis.insights, list)
    assert isinstance(analysis.recommendations, list)
    assert isinstance(analysis.key_risks, list)
    assert isinstance(analysis.opportunities, list)

    assert 0 <= analysis.overall_confidence <= 1

    for insight in analysis.insights:
        assert insight.title
        assert insight.finding
        assert insight.implication
        assert 0 <= insight.confidence <= 1
        assert insight.severity in {"low", "medium", "high", "critical"}
        assert isinstance(insight.evidence, list)

    for recommendation in analysis.recommendations:
        assert recommendation.title
        assert recommendation.action
        assert recommendation.rationale
        assert recommendation.expected_impact
        assert recommendation.priority in {"low", "medium", "high", "critical"}

    print("Executive summary:", analysis.executive_summary)
    print("Insights:", len(analysis.insights))
    print("Recommendations:", len(analysis.recommendations))
    print("Risks:", len(analysis.key_risks))
    print("Confidence:", analysis.overall_confidence)
    print("Structured intelligence validation: PASS")


def test_financial_analyst_node():
    print("\n=== Financial Analyst Node Test ===")

    result = financial_analyst_node(
        make_initial_state("Analyze our financial performance")
    )

    assert result["current_agent"] == "financial_analyst"
    assert result["analyst_findings"]

    finding = result["analyst_findings"][0]

    assert finding["status"] == "success"
    assert finding["metrics"]["revenue"] > 0
    assert finding["metrics"]["gross_profit"] > 0

    analysis = finding["analysis"]

    assert analysis["executive_summary"]
    assert isinstance(analysis["insights"], list)
    assert isinstance(analysis["recommendations"], list)
    assert "overall_confidence" in analysis

    assert result["evidence"]
    assert result["agent_trace"]

    print("Entity:", finding["entity"])
    print("Period:", finding["context"]["latest_period"])
    print("Reasoning mode:", finding["reasoning_mode"])
    print("Insights:", len(analysis["insights"]))
    print("Recommendations:", len(analysis["recommendations"]))
    print("Node validation: PASS")

def test_financial_data_reliability():
    print("\n=== Financial Data Reliability Tests ===")

    # 1. Invalid numeric values must be treated as missing.
    context = build_financial_context({
        "entity": "TEST",
        "kpis": {
            "revenue": float("nan"),
            "cost_of_sales": float("inf"),
            "supplier_invoices": "invalid",
            "gross_profit": 100,
            "gross_margin_pct": 30,
        },
        "history": [],
    })

    financials = context["current_financials"]

    assert financials["revenue"] is None
    assert financials["cost_of_sales"] is None
    assert financials["supplier_invoices"] is None

    analysis = deterministic_analysis(context)
    assert analysis.analysis_status == "partial"
    assert abs(analysis.overall_confidence - 0.4) < 1e-9

    print("Invalid numeric values: PASS")

    # 2. No available KPI data must produce insufficient_data.
    context = build_financial_context({
        "entity": "TEST",
        "kpis": {
            "revenue": None,
            "cost_of_sales": None,
            "supplier_invoices": None,
            "gross_profit": None,
            "gross_margin_pct": None,
        },
        "history": [],
    })

    analysis = deterministic_analysis(context)

    assert analysis.analysis_status == "insufficient_data"
    assert analysis.overall_confidence == 0.0
    assert not analysis.insights
    assert analysis.data_limitations

    print("All KPI values missing: PASS")

    # 3. Incomplete historical values must not produce false comparisons.
    context = build_financial_context({
        "entity": "TEST",
        "kpis": {
            "revenue": 200,
            "cost_of_sales": 120,
            "supplier_invoices": 40,
            "gross_profit": 80,
            "gross_margin_pct": 40,
        },
        "history": [
            {
                "revenue": None,
                "cost_of_sales": 100,
                "gross_profit": 0,
            },
            {
                "revenue": 200,
                "cost_of_sales": 120,
                "gross_profit": 80,
            },
        ],
    })

    comparison = context["historical_comparison"]

    assert comparison["revenue_change_pct"] is None
    assert comparison["cost_of_sales_change_pct"] == 20.0
    assert comparison["gross_profit_change_pct"] is None

    analysis = deterministic_analysis(context)

    assert analysis.analysis_status == "partial"
    assert any(
        "historical comparisons" in item.lower()
        for item in analysis.data_limitations
    )
    assert not any(
        insight.title == "Cost growth outpacing revenue"
        for insight in analysis.insights
    )

    print("Incomplete historical comparisons: PASS")
    print("Financial data reliability: PASS")



def test_end_to_end():
    print("\n=== End-to-End Graph Test ===")

    result = ledgerlens_graph.invoke(
        make_initial_state("Analyze our revenue and profitability")
    )

    assert result["current_agent"] == "financial_analyst"
    assert result["analyst_findings"]
    assert result["evidence"]

    finding = result["analyst_findings"][-1]
    analysis = finding["analysis"]

    assert finding["status"] == "success"
    assert analysis["executive_summary"]
    assert analysis["entity"] == "LOG"

    print("Agent:", result["current_agent"])
    print("Revenue:", finding["metrics"]["revenue"])
    print("Gross profit:", finding["metrics"]["gross_profit"])
    print("Gross margin:", round(finding["metrics"]["gross_margin_pct"], 2))
    print("Insight count:", len(analysis["insights"]))
    print("Recommendation count:", len(analysis["recommendations"]))
    print("Trace:", result["agent_trace"])
    print("End-to-end validation: PASS")

def test_multi_agent_handoff():
    print("\n=== Multi-Agent Handoff Test ===")

    query = "What should we do to improve profitability?"
    result = ledgerlens_graph.invoke(make_initial_state(query))

    trace = result.get("agent_trace", [])
    investigation_findings = result.get("investigation_findings", [])
    actions = result.get("proposed_actions", [])

    assert result["current_agent"] == "decision_agent"
    assert investigation_findings, "Investigation Agent produced no findings"
    assert actions, "Decision Agent produced no actions"

    investigation_index = next(
        i for i, item in enumerate(trace)
        if item.startswith("investigation_agent:")
    )

    decision_index = next(
        i for i, item in enumerate(trace)
        if item.startswith("decision_agent:")
    )

    assert investigation_index < decision_index

    assert any(
        "trends_analyzed" in item for item in trace
    )

    assert any(
        "actions_generated" in item for item in trace
    )

    print("Investigation findings:", len(investigation_findings))
    print("Actions generated:", len(actions))
    print("Execution order: Investigation → Decision")
    print("Trace:", trace)
    print("Multi-agent validation: PASS")

def test_agent_contracts():
    print("\n=== Agent Contract Tests ===")

    from backend.agents.contracts import validate_agent_output

    valid_output = {
        "current_agent": "decision_agent",
        "proposed_actions": [{"action": "Test action"}],
        "agent_trace": ["decision_agent:actions_generated"],
        "errors": [],
    }

    invalid_output = {
        "current_agent": "forecast_agent",
        "proposed_actions": "invalid",
    }

    assert validate_agent_output("decision_agent", valid_output) == []

    errors = validate_agent_output("decision_agent", invalid_output)
    assert len(errors) > 0

    print("Valid output: PASS")
    print("Invalid output rejection: PASS")
    print("Agent contract validation: PASS")


def test_retry_behavior():
    print("\n=== Retry Behavior Tests ===")

    from backend.agents.graph import enforce_contract

    # 1. Immediate success
    calls = {"count": 0}

    def success_node(state):
        calls["count"] += 1
        return {
            "current_agent": "decision_agent",
            "proposed_actions": [],
            "agent_trace": [],
            "errors": [],
        }

    result = enforce_contract("decision_agent", success_node)({})
    assert calls["count"] == 1
    assert result["current_agent"] == "decision_agent"
    print("Immediate success: PASS")

    # 2. Fail once, then succeed
    calls = {"count": 0}

    def flaky_node(state):
        calls["count"] += 1

        if calls["count"] == 1:
            raise RuntimeError("Temporary failure")

        return {
            "current_agent": "decision_agent",
            "proposed_actions": [],
            "agent_trace": [],
            "errors": [],
        }

    result = enforce_contract("decision_agent", flaky_node)({})
    assert calls["count"] == 2
    assert result["current_agent"] == "decision_agent"
    print("Retry then success: PASS")

    # 3. Permanent failure
    calls = {"count": 0}

    def failing_node(state):
        calls["count"] += 1
        raise RuntimeError("Permanent failure")

    result = enforce_contract("decision_agent", failing_node)({})
    assert calls["count"] == 2
    assert result["errors"]
    assert "failed_after_retries" in result["agent_trace"][0]
    print("Retry limit and controlled failure: PASS")

    print("Retry validation: PASS")

def test_investigation_failure_blocks_decision():
    print("\n=== Failure Propagation Test ===")

    from backend.agents.graph import route_after_investigation, END

    state = {
        "user_query": "What should we do to improve profitability?",
        "agent_trace": [
            "investigation_agent:failed_after_retries"
        ],
    }

    result = route_after_investigation(state)

    assert result == END

    print("Failed investigation blocks Decision Agent: PASS")

def test_execution_budget():
    print("\n=== Execution Budget Test ===")

    from backend.agents.graph import enforce_contract

    calls = {"count": 0}

    def dummy_agent(state):
        calls["count"] += 1
        return {
            "current_agent": "financial_analyst",
            "analyst_findings": [],
            "agent_trace": ["financial_analyst:completed"],
            "errors": [],
        }

    wrapped_agent = enforce_contract(
        "financial_analyst",
        dummy_agent,
        max_retries=1,
    )

    state = {
        "agent_execution_count": 5,
        "max_agent_executions": 5,
        "agent_trace": [],
        "errors": [],
    }

    result = wrapped_agent(state)

    assert calls["count"] == 0
    assert result["execution_budget_exceeded"] is True
    assert result["agent_execution_count"] == 5

    print("Budget exhaustion blocks execution: PASS")

def test_retry_consumes_execution_budget():
    print("\n=== Retry Budget Accounting Test ===")

    from backend.agents.graph import enforce_contract

    calls = {"count": 0}

    def flaky_agent(state):
        calls["count"] += 1

        if calls["count"] == 1:
            raise RuntimeError("Temporary failure")

        return {
            "current_agent": "financial_analyst",
            "analyst_findings": [],
            "agent_trace": ["financial_analyst:completed"],
            "errors": [],
        }

    wrapped_agent = enforce_contract(
        "financial_analyst",
        flaky_agent,
        max_retries=1,
    )

    state = {
        "agent_execution_count": 0,
        "max_agent_executions": 1,
        "agent_trace": [],
        "errors": [],
    }

    result = wrapped_agent(state)

    assert calls["count"] == 1
    assert result["agent_execution_count"] == 1
    assert result["execution_budget_exceeded"] is True

    print("Retry consumes execution budget: PASS")

def test_execution_timing():
    print("\n=== Execution Timing Test ===")

    from backend.agents.graph import enforce_contract
    import time

    def dummy_agent(state):
        time.sleep(0.05)
        return {
            "current_agent": "financial_analyst",
            "analyst_findings": [],
            "agent_trace": ["financial_analyst:completed"],
            "errors": [],
        }

    wrapped = enforce_contract("financial_analyst", dummy_agent)

    result = wrapped({
        "agent_execution_count": 0,
        "max_agent_executions": 5,
        "agent_trace": [],
        "errors": [],
    })

    duration = result["execution_duration_ms"]

    assert duration >= 40
    assert any("duration:" in item for item in result["agent_trace"])

    print(f"Recorded duration: {duration:.2f}ms")
    print("Execution timing: PASS")

if __name__ == "__main__":
    tests = [
        test_agent_routing,
        test_financial_context,
        test_deterministic_intelligence,
        test_financial_analyst_node,
        test_financial_data_reliability,
        test_end_to_end,
        test_multi_agent_handoff,
        test_agent_contracts,
        test_retry_behavior,
        test_investigation_failure_blocks_decision,
        test_execution_budget,
        test_retry_consumes_execution_budget,
        test_execution_timing,
    ]

    failures = []

    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append((test.__name__, exc))
            print(f"\nFAIL: {test.__name__}: {exc}")

    print("\n" + "=" * 55)
    print(f"TESTS COMPLETED: {len(tests) - len(failures)}/{len(tests)} PASSED")

    if failures:
        print("FAILED TESTS:")
        for name, error in failures:
            print(f"- {name}: {error}")
        raise SystemExit(1)

    print("ALL TESTS PASSED")

def test_agent_contracts():
    print("\n=== Agent Contract Tests ===")

    from backend.agents.contracts import validate_agent_output

    valid_output = {
        "current_agent": "decision_agent",
        "proposed_actions": [{"action": "Test action"}],
        "agent_trace": ["decision_agent:actions_generated"],
        "errors": [],
    }

    invalid_output = {
        "current_agent": "forecast_agent",
        "proposed_actions": "invalid",
    }

    assert validate_agent_output("decision_agent", valid_output) == []

    errors = validate_agent_output("decision_agent", invalid_output)
    assert errors

    print("Valid output: PASS")
    print("Invalid output rejection: PASS")
    print("Agent contract validation: PASS")

