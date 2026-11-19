
from datetime import datetime


def _change(current, previous):
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def generate_financial_actions(data, entity):
    """
    Deterministic financial action engine.
    Detects changes using the latest two monthly records.
    """

    entity_data = (
        data[data["EntityCode"].astype(str).str.upper() == entity.upper()]
        .sort_values("MonthEnd")
        .copy()
    )

    if len(entity_data) < 2:
        return []

    latest = entity_data.iloc[-1]
    previous = entity_data.iloc[-2]

    actions = []

    current_revenue = float(latest["Revenue"])
    previous_revenue = float(previous["Revenue"])

    current_cost = float(latest["CostOfSales"])
    previous_cost = float(previous["CostOfSales"])

    current_supplier = float(latest["SupplierInvoices"])
    previous_supplier = float(previous["SupplierInvoices"])

    current_profit = current_revenue - current_cost
    previous_profit = previous_revenue - previous_cost

    current_margin = (
        current_profit / current_revenue * 100
        if current_revenue else 0
    )

    previous_margin = (
        previous_profit / previous_revenue * 100
        if previous_revenue else 0
    )

    period = str(latest["MonthEnd"].date())

    # 1. Revenue deterioration
    revenue_change = _change(current_revenue, previous_revenue)

    if revenue_change is not None and revenue_change <= -5:
        decline_amount = previous_revenue - current_revenue

        actions.append({
            "id": f"{entity}-revenue-{period}",
            "type": "revenue_decline",
            "severity": "high" if revenue_change <= -10 else "medium",
            "title": "Revenue decline detected",
            "trigger": f"Revenue decreased {abs(revenue_change):.1f}% month-over-month.",
            "financial_value": round(decline_amount, 2),
            "financial_value_label": "Revenue decrease vs previous month",
            "action": "Investigate sales performance, lost customers, order volume and pricing changes.",
            "automation": "Automatically created financial investigation task.",
            "status": "open",
            "period": period
        })

    # 2. Cost escalation
    cost_change = _change(current_cost, previous_cost)

    if cost_change is not None and cost_change >= 5:
        increase = current_cost - previous_cost

        actions.append({
            "id": f"{entity}-cost-{period}",
            "type": "cost_increase",
            "severity": "high" if cost_change >= 10 else "medium",
            "title": "Cost escalation detected",
            "trigger": f"Cost of sales increased {cost_change:.1f}% month-over-month.",
            "financial_value": round(increase, 2),
            "financial_value_label": "Additional monthly cost",
            "action": "Review supplier pricing, purchasing costs and production efficiency.",
            "automation": "Automatically created cost review task.",
            "status": "open",
            "period": period
        })

    # 3. Gross margin deterioration
    margin_change = current_margin - previous_margin

    if margin_change <= -2:
        actions.append({
            "id": f"{entity}-margin-{period}",
            "type": "margin_deterioration",
            "severity": "high" if margin_change <= -5 else "medium",
            "title": "Gross margin deterioration",
            "trigger": f"Gross margin declined {abs(margin_change):.2f} percentage points.",
            "financial_value": round(margin_change, 2),
            "financial_value_label": "Gross margin change (percentage points)",
            "action": "Review pricing, product mix, discounts and cost of sales.",
            "automation": "Automatically created margin investigation task.",
            "status": "open",
            "period": period
        })

    # 4. Supplier invoice pressure
    supplier_change = _change(current_supplier, previous_supplier)

    if supplier_change is not None and supplier_change >= 8:
        increase = current_supplier - previous_supplier

        actions.append({
            "id": f"{entity}-supplier-{period}",
            "type": "supplier_invoice_increase",
            "severity": "high" if supplier_change >= 15 else "medium",
            "title": "Supplier obligations increased",
            "trigger": f"Supplier invoices increased {supplier_change:.1f}% month-over-month.",
            "financial_value": round(increase, 2),
            "financial_value_label": "Increase in supplier invoices",
            "action": "Review upcoming supplier obligations, payment schedules and purchasing commitments.",
            "automation": "Automatically created payables review task.",
            "status": "open",
            "period": period
        })

    return actions
