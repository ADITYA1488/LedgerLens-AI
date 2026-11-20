
from typing import Any

from backend.agents.state import LedgerLensState
from backend.agents.nodes.financial_context import build_financial_context
from main import get_entity_analytics


def _severity(value: float, medium: float, high: float) -> str:
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def risk_agent_node(state: LedgerLensState) -> dict[str, Any]:
    entity = state.get("entity", "LOG").upper()
    query = state.get("user_query", "")

    try:
        analytics = get_entity_analytics(entity)
        context = build_financial_context(analytics)

        financials = context["current_financials"]
        ratios = context["financial_ratios"]
        comparison = context["historical_comparison"]

        risks = []
        risk_score = 0

        revenue = financials["revenue"]
        cost = financials["cost_of_sales"]
        gross_profit = financials["gross_profit"]
        gross_margin = financials["gross_margin_pct"]

        cost_ratio = ratios["cost_of_sales_to_revenue_pct"]
        supplier_ratio = ratios["supplier_invoices_to_revenue_pct"]

        # 1. Cost pressure
        if cost_ratio is not None and cost_ratio >= 80:
            risks.append({
                "risk": "High cost-of-sales burden",
                "category": "profitability",
                "severity": "high",
                "evidence": {
                    "cost_of_sales_to_revenue_pct": cost_ratio
                },
                "description": (
                    "Cost of sales consumes a large proportion of revenue, "
                    "limiting the remaining gross-profit contribution."
                ),
            })
            risk_score += 25

        elif cost_ratio is not None and cost_ratio >= 70:
            risks.append({
                "risk": "Elevated cost-of-sales burden",
                "category": "profitability",
                "severity": "medium",
                "evidence": {
                    "cost_of_sales_to_revenue_pct": cost_ratio
                },
                "description": (
                    "Cost of sales is relatively high compared with revenue."
                ),
            })
            risk_score += 15

        # 2. Gross margin
        if gross_margin is not None and gross_margin < 20:
            risks.append({
                "risk": "Low gross margin",
                "category": "margin",
                "severity": "high",
                "evidence": {"gross_margin_pct": gross_margin},
                "description": (
                    "Low gross margin leaves limited room to absorb "
                    "operating expenses or unexpected costs."
                ),
            })
            risk_score += 25

        elif gross_margin is not None and gross_margin < 35:
            risks.append({
                "risk": "Margin pressure",
                "category": "margin",
                "severity": "medium",
                "evidence": {"gross_margin_pct": gross_margin},
                "description": (
                    "Gross margin may warrant monitoring to protect "
                    "profitability."
                ),
            })
            risk_score += 15

        # 3. Revenue decline
        revenue_change = comparison.get("revenue_change_pct")

        if revenue_change is not None and revenue_change <= -10:
            risks.append({
                "risk": "Significant revenue decline",
                "category": "revenue",
                "severity": "high",
                "evidence": {"revenue_change_pct": revenue_change},
                "description": (
                    "Revenue declined substantially across the available "
                    "comparison period."
                ),
            })
            risk_score += 25

        elif revenue_change is not None and revenue_change < 0:
            risks.append({
                "risk": "Revenue contraction",
                "category": "revenue",
                "severity": "medium",
                "evidence": {"revenue_change_pct": revenue_change},
                "description": (
                    "Revenue declined across the available comparison period."
                ),
            })
            risk_score += 15

        # 4. Cost growth outpacing revenue
        cost_change = comparison.get("cost_of_sales_change_pct")

        if (
            revenue_change is not None
            and cost_change is not None
            and cost_change > revenue_change
        ):
            severity = (
                "high"
                if cost_change - revenue_change >= 10
                else "medium"
            )

            risks.append({
                "risk": "Costs growing faster than revenue",
                "category": "cost",
                "severity": severity,
                "evidence": {
                    "revenue_change_pct": revenue_change,
                    "cost_of_sales_change_pct": cost_change,
                },
                "description": (
                    "Cost of sales growth exceeded revenue growth, "
                    "creating potential margin pressure."
                ),
            })

            risk_score += 20 if severity == "high" else 12

        # 5. Gross profit decline
        gross_profit_change = comparison.get("gross_profit_change_pct")

        if gross_profit_change is not None and gross_profit_change < -10:
            risks.append({
                "risk": "Significant gross-profit decline",
                "category": "profitability",
                "severity": "high",
                "evidence": {
                    "gross_profit_change_pct": gross_profit_change
                },
                "description": (
                    "Gross profit declined significantly across the "
                    "available comparison period."
                ),
            })
            risk_score += 20

        elif gross_profit_change is not None and gross_profit_change < 0:
            risks.append({
                "risk": "Gross-profit deterioration",
                "category": "profitability",
                "severity": "medium",
                "evidence": {
                    "gross_profit_change_pct": gross_profit_change
                },
                "description": (
                    "Gross profit declined across the comparison period."
                ),
            })
            risk_score += 12

        # 6. Supplier invoice concentration indicator
        if supplier_ratio is not None and supplier_ratio >= 90:
            risks.append({
                "risk": "Elevated supplier-invoice exposure",
                "category": "supplier",
                "severity": "high",
                "evidence": {
                    "supplier_invoices_to_revenue_pct": supplier_ratio
                },
                "description": (
                    "Supplier invoices are high relative to revenue. "
                    "This is an exposure indicator, not a direct measurement "
                    "of cash flow, overdue liabilities, or supplier concentration."
                ),
            })
            risk_score += 20

        elif supplier_ratio is not None and supplier_ratio >= 75:
            risks.append({
                "risk": "Supplier-invoice exposure",
                "category": "supplier",
                "severity": "medium",
                "evidence": {
                    "supplier_invoices_to_revenue_pct": supplier_ratio
                },
                "description": (
                    "Supplier invoices are substantial relative to revenue "
                    "and may warrant monitoring."
                ),
            })
            risk_score += 10

        risk_score = min(risk_score, 100)

        if risk_score >= 70:
            overall_level = "high"
        elif risk_score >= 35:
            overall_level = "medium"
        else:
            overall_level = "low"

        result = {
            "agent": "risk_agent",
            "entity": entity,
            "query": query,
            "status": "success",
            "risk_score": risk_score,
            "overall_risk": overall_level,
            "risk_count": len(risks),
            "risks": risks,
            "financial_context": context,
            "methodology": (
                "Rule-based indicators derived from available financial "
                "metrics and first-to-last historical comparisons. "
                "Score is a heuristic, not a probability of loss."
            ),
        }

        return {
            "current_agent": "risk_agent",
            "risk_findings": [result],
            "evidence": [{
                "source": "financial_analytics_engine",
                "entity": entity,
                "risk_score": risk_score,
                "risk_count": len(risks),
            }],
            "agent_trace": [
                "risk_agent:analytics_retrieved",
                "risk_agent:indicators_evaluated",
                "risk_agent:risk_assessment_completed",
            ],
        }

    except Exception as exc:
        return {
            "current_agent": "risk_agent",
            "risk_findings": [{
                "agent": "risk_agent",
                "entity": entity,
                "query": query,
                "status": "error",
                "error": str(exc),
            }],
            "errors": [f"risk_agent: {str(exc)}"],
            "agent_trace": ["risk_agent:execution_failed"],
        }
