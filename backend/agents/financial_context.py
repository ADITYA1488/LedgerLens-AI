from typing import Any


def safe_percentage_change(previous: float, current: float) -> float | None:
    if previous == 0:
        return None

    return ((current - previous) / abs(previous)) * 100


def build_financial_context(analytics: dict[str, Any]) -> dict[str, Any]:
    kpis = analytics.get("kpis", {})
    history = analytics.get("history", [])

    revenue = float(kpis.get("revenue", 0))
    cost_of_sales = float(kpis.get("cost_of_sales", 0))
    supplier_invoices = float(kpis.get("supplier_invoices", 0))
    gross_profit = float(kpis.get("gross_profit", 0))
    gross_margin_pct = kpis.get("gross_margin_pct")

    historical_comparison = {}

    if len(history) >= 2:
        first = history[0]
        latest = history[-1]

        historical_comparison = {
            "comparison_start": first.get("period"),
            "comparison_end": latest.get("period"),
            "revenue_change_pct": safe_percentage_change(
                float(first.get("revenue", 0)),
                float(latest.get("revenue", 0)),
            ),
            "cost_of_sales_change_pct": safe_percentage_change(
                float(first.get("cost_of_sales", 0)),
                float(latest.get("cost_of_sales", 0)),
            ),
            "gross_profit_change_pct": safe_percentage_change(
                float(first.get("gross_profit", 0)),
                float(latest.get("gross_profit", 0)),
            ),
        }

    return {
        "entity": analytics.get("entity"),
        "dataset": analytics.get("dataset"),
        "dataset_type": analytics.get("dataset_type"),
        "currency": analytics.get("currency"),
        "latest_period": analytics.get("latest_period"),
        "current_financials": {
            "revenue": revenue,
            "cost_of_sales": cost_of_sales,
            "supplier_invoices": supplier_invoices,
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin_pct,
        },
        "financial_ratios": {
            "cost_of_sales_to_revenue_pct": (
                cost_of_sales / revenue * 100 if revenue else None
            ),
            "supplier_invoices_to_revenue_pct": (
                supplier_invoices / revenue * 100 if revenue else None
            ),
        },
        "historical_comparison": historical_comparison,
        "history_months_available": len(history),
    }