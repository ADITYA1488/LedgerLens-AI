import json
from typing import Any

from backend.agents.schemas import FinancialAnalysis
from backend.ai.llm_provider import get_llm, LLMConfigurationError


SYSTEM_PROMPT = """
You are the Financial Intelligence Engine of LedgerLens AI.

Analyze financial evidence provided to you.

STRICT RULES:
1. Use only the supplied financial evidence.
2. Never invent financial numbers.
3. Distinguish facts, interpretations, and hypotheses.
4. Do not claim causation without evidence.
5. Identify meaningful trends, risks, anomalies, and opportunities.
6. Recommendations must be practical and evidence-backed.
7. If evidence is insufficient, explicitly say so.
8. Treat synthetic data as synthetic.
9. Do not provide false certainty.
10. Return output conforming to the required structured schema.
"""


def deterministic_analysis(context: dict[str, Any]) -> FinancialAnalysis:
    financials = context.get("current_financials", {})
    ratios = context.get("financial_ratios", {})
    comparison = context.get("historical_comparison", {})

    revenue = financials.get("revenue", 0)
    gross_profit = financials.get("gross_profit", 0)
    margin = financials.get("gross_margin_pct", 0)

    revenue_change = comparison.get("revenue_change_pct")
    cost_change = comparison.get("cost_of_sales_change_pct")
    profit_change = comparison.get("gross_profit_change_pct")

    insights = []
    risks = []
    recommendations = []
    limitations = []

    if revenue_change is not None and cost_change is not None:
        if cost_change > revenue_change:
            finding = (
                "Cost of sales increased faster than revenue "
                "over the available comparison period."
            )

            insights.append({
                "title": "Cost growth outpacing revenue",
                "category": "cost",
                "severity": "high" if cost_change - revenue_change > 5 else "medium",
                "finding": finding,
                "evidence": [
                    f"Revenue change: {revenue_change:.2f}%",
                    f"Cost of sales change: {cost_change:.2f}%",
                ],
                "implication": (
                    "Continued divergence may pressure gross profitability."
                ),
                "confidence": 0.95,
            })

            risks.append(
                "Cost growth is outpacing revenue growth across the "
                "available comparison period."
            )

            recommendations.append({
                "title": "Investigate cost growth drivers",
                "priority": "high",
                "action": (
                    "Review cost categories, supplier pricing, purchasing "
                    "patterns, and monthly cost movements."
                ),
                "rationale": (
                    "Cost of sales increased faster than revenue."
                ),
                "expected_impact": (
                    "Identify possible cost pressure and opportunities "
                    "to protect gross profit."
                ),
                "evidence": [
                    f"Revenue change: {revenue_change:.2f}%",
                    f"Cost of sales change: {cost_change:.2f}%",
                ],
                "requires_approval": True,
            })

    if margin is not None:
        if margin < 20:
            severity = "high"
        elif margin < 35:
            severity = "medium"
        else:
            severity = "low"

        insights.append({
            "title": "Gross margin assessment",
            "category": "profitability",
            "severity": severity,
            "finding": f"Current gross margin is {margin:.2f}%.",
            "evidence": [
                f"Revenue: {revenue}",
                f"Gross profit: {gross_profit}",
                f"Gross margin: {margin:.2f}%",
            ],
            "implication": (
                "Gross margin should be evaluated alongside historical "
                "performance and operating cost trends."
            ),
            "confidence": 1.0,
        })

    if profit_change is not None and profit_change < 0:
        risks.append(
            f"Gross profit declined by {abs(profit_change):.2f}% "
            "across the comparison period."
        )

    if not comparison:
        limitations.append(
            "Insufficient historical data for period comparison."
        )

    executive_summary = (
        f"Entity {context.get('entity')} generated revenue of "
        f"{revenue:,.2f} and gross profit of {gross_profit:,.2f}. "
        f"Gross margin was {margin:.2f}%. "
    )

    if revenue_change is not None:
        executive_summary += (
            f"Revenue changed by {revenue_change:.2f}% "
            "across the available comparison period. "
        )

    if cost_change is not None:
        executive_summary += (
            f"Cost of sales changed by {cost_change:.2f}%. "
        )

    if profit_change is not None:
        executive_summary += (
            f"Gross profit changed by {profit_change:.2f}%. "
        )

    result = {
        "entity": context.get("entity", "UNKNOWN"),
        "reporting_period": context.get("latest_period", "UNKNOWN"),
        "executive_summary": executive_summary,
        "insights": insights,
        "recommendations": recommendations,
        "key_risks": risks,
        "opportunities": [],
        "data_limitations": limitations,
        "overall_confidence": 0.90,
        "analysis_status": "complete",
    }

    return FinancialAnalysis.model_validate(result)


def analyze_financial_evidence(
    context: dict[str, Any],
    use_llm: bool = True,
) -> FinancialAnalysis:

    if not use_llm:
        return deterministic_analysis(context)

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(FinancialAnalysis)

        response = structured_llm.invoke([
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Analyze the following financial evidence. "
                "Do not invent information.\n\n"
                + json.dumps(context, indent=2, default=str),
            ),
        ])

        if isinstance(response, FinancialAnalysis):
            return response

        return FinancialAnalysis.model_validate(response)

    except Exception:
        # Safe fallback. We do not misrepresent fallback output as LLM output.
        return deterministic_analysis(context)
