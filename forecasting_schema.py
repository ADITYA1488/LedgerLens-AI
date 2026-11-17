
from typing import Optional, List
from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    period: str
    predicted_value: float


class EvaluationMetrics(BaseModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    smape: Optional[float] = None
    bias: Optional[float] = None


class ForecastMetadata(BaseModel):
    dataset: str
    dataset_type: str
    currency: str
    training_end: Optional[str] = None


class ForecastResponse(BaseModel):
    entity: str
    target: str
    forecast_frequency: str = "monthly"
    model: str
    forecast: List[ForecastPoint]
    evaluation: EvaluationMetrics
    metadata: ForecastMetadata
