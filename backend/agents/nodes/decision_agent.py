from typing import Any

from backend.agents.state import LedgerLensState


def decision_agent_node(state: LedgerLensState) -> dict[str, Any]:
    entity = state.get("entity", "LOG")
    query = state.get("user_query", "")

    try:
        analyst_findings = state.get("analyst_findings", [])
        risk_findings = state.get("risk_findings", [])
        investigation_findings = state.get("investigation_findings", [])

        actions = []

        # Extract investigation evidence
        investigation = (
            investigation_findings[-1]
            if investigation_findings
            else {}
        )

        findings = investigation.get("findings", [])
        hypotheses = investigation.get("hypotheses", [])

        # -------------------------------------------------
        # Action 1: Cost optimization
        # -------------------------------------------------
        cost_growth = any(
            "cost of sales increased" in str(f.get("finding", "")).lower()
            for f in findings
        )

        costs_outpacing_revenue = any(
            "costs are growing faster than revenue"
            in str(f.get("finding", "")).lower()
            for f in findings
        )

        if cost_growth or costs_outpacing_revenue:
            actions.append({
                "action_id": "DA-COST-001",
                "entity": entity,
                "title": "Investigate and control cost growth",
                "description": (
                    "Review cost-of-sales trends, supplier pricing, "
                    "purchase volumes, and high-cost categories. Identify "
                    "specific cost drivers before implementing reductions."
                ),
                "priority": "high",
                "category": "cost_optimization",
                "owner_role": "Finance / Procurement",
                "success_metric": "Cost-of-sales growth decreases relative to revenue growth",
                "approval_required": True,
                "status": "open",
                "evidence": [
                    f["finding"]
                    for f in findings
                    if "cost" in str(f.get("finding", "")).lower()
                ],
            })

        # -------------------------------------------------
        # Action 2: Revenue stabilization
        # -------------------------------------------------
        revenue_declining = any(
            "revenue declined" in str(f.get("finding", "")).lower()
            for f in findings
        )

        if revenue_declining:
            actions.append({
                "action_id": "DA-REV-001",
                "entity": entity,
                "title": "Investigate revenue contraction",
                "description": (
                    "Analyze customer segments, sales volumes, "
                    "pricing changes, and revenue concentration to "
                    "identify the causes of revenue decline."
                ),
                "priority": "high",
                "category": "revenue_growth",
                "owner_role": "Sales / Finance",
                "success_metric": "Revenue returns to a positive growth trajectory",
                "approval_required": False,
                "status": "open",
                "evidence": [
                    f["finding"]
                    for f in findings
                    if "revenue" in str(f.get("finding", "")).lower()
                ],
            })

        # -------------------------------------------------
        # Action 3: Margin protection
        # -------------------------------------------------
        gross_profit_declining = any(
            "gross profit declined" in str(f.get("finding", "")).lower()
            for f in findings
        )

        if gross_profit_declining:
            actions.append({
                "action_id": "DA-MARGIN-001",
                "entity": entity,
                "title": "Protect gross profit margin",
                "description": (
                    "Review product and service margins, pricing, "
                    "cost structure, and low-margin operations. "
                    "Identify opportunities to improve gross profitability."
                ),
                "priority": "high",
                "category": "profitability",
                "owner_role": "Finance / Business Operations",
                "success_metric": "Gross margin improves from its current baseline",
                "approval_required": True,
                "status": "open",
                "evidence": [
                    f["finding"]
                    for f in findings
                    if "gross profit" in str(f.get("finding", "")).lower()
                ],
            })

        # -------------------------------------------------
        # Action 4: Validate hypotheses
        # -------------------------------------------------
        if hypotheses:
            actions.append({
                "action_id": "DA-INV-001",
                "entity": entity,
                "title": "Validate financial deterioration hypotheses",
                "description": (
                    "Validate the identified hypotheses using "
                    "transaction-level records, supplier invoices, "
                    "sales data, and operational evidence. "
                    "Separate confirmed causes from assumptions."
                ),
                "priority": "medium",
                "category": "investigation",
                "owner_role": "Financial Analyst",
                "success_metric": "Root causes validated with supporting evidence",
                "approval_required": False,
                "status": "open",
                "evidence": [
                    h.get("hypothesis", "")
                    for h in hypotheses
                ],
            })

        # Prioritize actions
        priority_order = {
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        actions.sort(
            key=lambda action: priority_order.get(
                action["priority"], 99
            )
        )

        result = {
            "agent": "decision_agent",
            "entity": entity,
            "query": query,
            "status": "success",
            "actions": actions,
            "total_actions": len(actions),
            "decision_method": "evidence_based_rule_engine",
            "limitations": [
                "Expected impacts are not quantified without sufficient data.",
                "Actions require human review before execution.",
                "Recommendations are based on available financial evidence.",
            ],
        }

        return {
            "current_agent": "decision_agent",
            "proposed_actions": actions,
            "evidence": [{
                "source": "investigation_agent",
                "entity": entity,
                "actions_generated": len(actions),
            }],
            "agent_trace": [
                "decision_agent:findings_retrieved",
                "decision_agent:actions_generated",
                "decision_agent:actions_prioritized",
            ],
        }

    except Exception as exc:
        return {
            "current_agent": "decision_agent",
            "errors": [f"decision_agent: {str(exc)}"],
            "agent_trace": [
                "decision_agent:execution_failed"
            ],
        }