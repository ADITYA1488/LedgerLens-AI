
import math
from typing import Any


def optional_float(value: Any) -> float | None:
    """Convert a value to a finite float; preserve missing/invalid values."""
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    return result if math.isfinite(result) else None


def safe_percentage_change(
    previous: float | None,
    current: float | None,
) -> float | None:
    if previous is None or current is None or previous == 0:
        return None

    return ((current - previous) / abs(previous)) * 100


def build_financial_context(analytics: dict[str, Any]) -> dict[str, Any]:
    kpis = analytics.get("kpis") or {}
    history = analytics.get("history") or []

    revenue = optional_float(kpis.get("revenue"))
    cost_of_sales = optional_float(kpis.get("cost_of_sales"))
    supplier_invoices = optional_float(kpis.get("supplier_invoices"))
    gross_profit = optional_float(kpis.get("gross_profit"))
    gross_margin_pct = optional_float(kpis.get("gross_margin_pct"))

    comparison = {}

    if len(history) >= 2:
        first, latest = history[0], history[-1]

        comparison = {
            "comparison_start": first.get("period"),
            "comparison_end": latest.get("period"),
            "revenue_change_pct": safe_percentage_change(
                optional_float(first.get("revenue")),
                optional_float(latest.get("revenue")),
            ),
            "cost_of_sales_change_pct": safe_percentage_change(
                optional_float(first.get("cost_of_sales")),
                optional_float(latest.get("cost_of_sales")),
            ),
            "gross_profit_change_pct": safe_percentage_change(
                optional_float(first.get("gross_profit")),
                optional_float(latest.get("gross_profit")),
            ),
        }

    missing_fields = [
        field
        for field, value in {
            "revenue": revenue,
            "cost_of_sales": cost_of_sales,
            "supplier_invoices": supplier_invoices,
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin_pct,
        }.items()
        if value is None
    ]

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
                cost_of_sales / revenue * 100
                if cost_of_sales is not None
                and revenue is not None
                and revenue != 0
                else None
            ),
            "supplier_invoices_to_revenue_pct": (
                supplier_invoices / revenue * 100
                if supplier_invoices is not None
                and revenue is not None
                and revenue != 0
                else None
            ),
        },
        "historical_comparison": comparison,
        "history_months_available": len(history),
        "missing_current_fields": missing_fields,
    }
