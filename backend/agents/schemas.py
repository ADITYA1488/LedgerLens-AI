from typing import Literal
from pydantic import BaseModel, Field


class FinancialInsight(BaseModel):
    title: str
    category: Literal[
        "revenue",
        "profitability",
        "cost",
        "cash_flow",
        "supplier",
        "risk",
        "trend",
        "anomaly",
        "opportunity",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    finding: str
    evidence: list[str] = Field(default_factory=list)
    implication: str
    confidence: float = Field(ge=0.0, le=1.0)


class FinancialRecommendation(BaseModel):
    title: str
    priority: Literal["low", "medium", "high", "critical"]
    action: str
    rationale: str
    expected_impact: str
    evidence: list[str] = Field(default_factory=list)
    requires_approval: bool = True


class FinancialAnalysis(BaseModel):
    entity: str
    reporting_period: str

    executive_summary: str

    insights: list[FinancialInsight] = Field(default_factory=list)
    recommendations: list[FinancialRecommendation] = Field(default_factory=list)

    key_risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)

    overall_confidence: float = Field(ge=0.0, le=1.0)
    analysis_status: Literal[
        "complete",
        "partial",
        "insufficient_data",
    ] = "complete"
