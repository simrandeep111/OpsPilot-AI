from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.metric import MetricSnapshot


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    service: str
    problem_type: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["active", "resolved"] = "active"
    incident_probability: float = Field(ge=0, le=1)
    classification_confidence: float = Field(ge=0, le=1)
    metrics: MetricSnapshot
    likely_cause: str
    recommended_action: str
    analysis_source: str
    affected_resources: list[str] = Field(default_factory=list)
    source_context: dict = Field(default_factory=dict)
    jev_answers: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
