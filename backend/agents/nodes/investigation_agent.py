from typing import Any

from backend.agents.state import LedgerLensState
from backend.agents.nodes.financial_context import build_financial_context
from main import get_entity_analytics


def investigation_agent_node(state: LedgerLensState) -> dict[str, Any]:
    entity = state.get("entity", "LOG")
    query = state.get("user_query", "")

    try:
        analytics = get_entity_analytics(entity)
        context = build_financial_context(analytics)

        current = context["current_financials"]
        comparison = context["historical_comparison"]

        revenue_change = comparison.get("revenue_change_pct")
        cost_change = comparison.get("cost_of_sales_change_pct")
        gross_profit_change = comparison.get("gross_profit_change_pct")

        findings = []
        hypotheses = []

        # Revenue investigation
        if revenue_change is not None:
            if revenue_change < 0:
                findings.append({
                    "finding": "Revenue declined over the comparison period.",
                    "value": revenue_change,
                    "evidence": "Historical revenue comparison",
                    "type": "observed",
                })
                hypotheses.append({
                    "hypothesis": "Revenue contraction may be contributing to profitability pressure.",
                    "confidence": "medium",
                    "basis": "Observed revenue decline",
                    "requires_validation": True,
                })

        # Cost investigation
        if cost_change is not None:
            if cost_change > 0:
                findings.append({
                    "finding": "Cost of sales increased over the comparison period.",
                    "value": cost_change,
                    "evidence": "Historical cost of sales comparison",
                    "type": "observed",
                })

        # Revenue vs cost growth
        if revenue_change is not None and cost_change is not None:
            if cost_change > revenue_change:
                gap = cost_change - revenue_change

                findings.append({
                    "finding": "Costs are growing faster than revenue.",
                    "value": gap,
                    "evidence": "Comparison of revenue and cost growth",
                    "type": "observed",
                })

                hypotheses.append({
                    "hypothesis": (
                        "Cost growth exceeding revenue growth may be "
                        "contributing to margin deterioration."
                    ),
                    "confidence": "high",
                    "basis": {
                        "revenue_change_pct": revenue_change,
                        "cost_change_pct": cost_change,
                        "growth_gap_percentage_points": gap,
                    },
                    "requires_validation": True,
                })

        # Gross profit investigation
        if gross_profit_change is not None and gross_profit_change < 0:
            findings.append({
                "finding": "Gross profit declined over the comparison period.",
                "value": gross_profit_change,
                "evidence": "Historical gross profit comparison",
                "type": "observed",
            })

            hypotheses.append({
                "hypothesis": (
                    "The combination of revenue pressure and increasing "
                    "costs may explain gross profit deterioration."
                ),
                "confidence": "medium",
                "basis": "Revenue and cost trend comparison",
                "requires_validation": True,
            })

        result = {
            "agent": "investigation_agent",
            "entity": entity,
            "query": query,
            "status": "success",
            "findings": findings,
            "hypotheses": hypotheses,
            "financial_snapshot": current,
            "investigation_method": "evidence_based_trend_analysis",
            "limitations": [
                "Correlations and trends do not establish causation.",
                "Transaction-level investigation may be required to verify hypotheses.",
            ],
        }

        evidence = [{
            "source": "financial_analytics_engine",
            "entity": entity,
            "findings_count": len(findings),
            "hypotheses_count": len(hypotheses),
        }]

        return {
            "current_agent": "investigation_agent",
            "investigation_findings": [result],
            "evidence": evidence,
            "agent_trace": [
                "investigation_agent:analytics_retrieved",
                "investigation_agent:trends_analyzed",
                "investigation_agent:hypotheses_generated",
            ],
        }

    except Exception as exc:
        return {
            "current_agent": "investigation_agent",
            "investigation_findings": [{
                "agent": "investigation_agent",
                "entity": entity,
                "query": query,
                "status": "error",
                "error": str(exc),
            }],
            "errors": [f"investigation_agent: {str(exc)}"],
            "agent_trace": ["investigation_agent:execution_failed"],
        }