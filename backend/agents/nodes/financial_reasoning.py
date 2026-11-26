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
11. Insight confidence represents evidence coverage, NOT the probability
    that an insight is correct.
12. Assign insight confidence based on the availability and completeness
    of the specific evidence supporting that insight.
13. Overall confidence represents the proportion of the five current
    financial KPI fields available: revenue, cost_of_sales,
    supplier_invoices, gross_profit, and gross_margin_pct.
14. Do not assign high confidence merely because an interpretation
    appears plausible. Missing or invalid evidence must reduce
    confidence or be reported as a data limitation.
"""



def deterministic_analysis(context: dict[str, Any]) -> FinancialAnalysis:
    financials = context.get("current_financials", {})
    comparison = context.get("historical_comparison", {})

    revenue = financials.get("revenue")
    gross_profit = financials.get("gross_profit")
    margin = financials.get("gross_margin_pct")

    revenue_change = comparison.get("revenue_change_pct")
    cost_change = comparison.get("cost_of_sales_change_pct")
    profit_change = comparison.get("gross_profit_change_pct")

    insights = []
    risks = []
    recommendations = []
    limitations = []

    missing_fields = context.get("missing_current_fields", [])

    if missing_fields:
        limitations.append(
            "Current financial data is incomplete. Missing or invalid fields: "
            + ", ".join(missing_fields)
            + "."
        )

    # Compare revenue and cost only when both changes are available.
    if revenue_change is not None and cost_change is not None:
        if cost_change > revenue_change:
            difference = cost_change - revenue_change

            evidence = [
                f"Revenue change: {revenue_change:.2f}%",
                f"Cost of sales change: {cost_change:.2f}%",
            ]

            insights.append({
                "title": "Cost growth outpacing revenue",
                "category": "cost",
                "severity": "high" if difference > 5 else "medium",
                "finding": (
                    "Cost of sales increased faster than revenue "
                    "over the available comparison period."
                ),
                "evidence": evidence,
                "implication": (
                    "Continued divergence may pressure gross profitability."
                ),
                # Evidence coverage score, not a calibrated probability.
                "confidence": 1.0,
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
                "evidence": evidence,
                "requires_approval": True,
            })

    # Do not interpret a missing margin as a genuine zero margin.
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
                f"Revenue: {revenue:,.2f}" if revenue is not None
                else "Revenue: unavailable",
                f"Gross profit: {gross_profit:,.2f}"
                if gross_profit is not None
                else "Gross profit: unavailable",
                f"Gross margin: {margin:.2f}%",
            ],
            "implication": (
                "Gross margin should be evaluated alongside historical "
                "performance and operating cost trends."
            ),
            # The margin value is available; this is evidence coverage.
            "confidence": 1.0,
        })
    else:
        limitations.append(
            "Gross margin assessment unavailable because valid margin data "
            "was not provided."
        )

    if profit_change is not None and profit_change < 0:
        risks.append(
            f"Gross profit declined by {abs(profit_change):.2f}% "
            "across the comparison period."
        )

    if not comparison:
        limitations.append(
            "Insufficient historical data for period comparison."
        )
    elif any(
        value is None
        for value in (revenue_change, cost_change, profit_change)
    ):
        limitations.append(
            "Some historical comparisons could not be calculated because "
            "required period values were missing or zero."
        )

    available_metrics = [
        revenue,
        financials.get("cost_of_sales"),
        financials.get("supplier_invoices"),
        gross_profit,
        margin,
    ]

    available_count = sum(value is not None for value in available_metrics)
    data_coverage = available_count / len(available_metrics)

    if available_count == 0:
        status = "insufficient_data"
    elif available_count < len(available_metrics) or limitations:
        status = "partial"
    else:
        status = "complete"

    summary_parts = []

    entity = context.get("entity", "UNKNOWN")
    summary_parts.append(f"Financial analysis for entity {entity}.")

    if revenue is not None:
        summary_parts.append(f"Revenue was {revenue:,.2f}.")
    else:
        summary_parts.append("Revenue data is unavailable.")

    if gross_profit is not None:
        summary_parts.append(f"Gross profit was {gross_profit:,.2f}.")
    else:
        summary_parts.append("Gross profit data is unavailable.")

    if margin is not None:
        summary_parts.append(f"Gross margin was {margin:.2f}%.")
    else:
        summary_parts.append("Gross margin data is unavailable.")

    if revenue_change is not None:
        summary_parts.append(
            f"Revenue changed by {revenue_change:.2f}%."
        )

    if cost_change is not None:
        summary_parts.append(
            f"Cost of sales changed by {cost_change:.2f}%."
        )

    if profit_change is not None:
        summary_parts.append(
            f"Gross profit changed by {profit_change:.2f}%."
        )

    executive_summary = " ".join(summary_parts)

    result = {
        "entity": entity,
        "reporting_period": context.get("latest_period") or "UNKNOWN",
        "executive_summary": executive_summary,
        "insights": insights,
        "recommendations": recommendations,
        "key_risks": risks,
        "opportunities": [],
        "data_limitations": limitations,
        # Data coverage, not a calibrated probability of correctness.
        "overall_confidence": data_coverage,
        "analysis_status": status,
    }

    return FinancialAnalysis.model_validate(result)



def analyze_financial_evidence(
    context: dict[str, Any],
    use_llm: bool = True,
) -> tuple[FinancialAnalysis, str, str | None]:

    if not use_llm:
        return deterministic_analysis(context), "deterministic", None

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
            analysis = response
        else:
            analysis = FinancialAnalysis.model_validate(response)

        return analysis, "gemini", None

    except Exception as exc:
        fallback_reason = type(exc).__name__
        return deterministic_analysis(context), "deterministic_fallback", fallback_reason
