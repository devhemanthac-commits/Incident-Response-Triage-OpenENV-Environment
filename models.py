from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Any


class TriageObservation(BaseModel):
    task_id: str
    incident_id: str
    step_number: int
    feedback: str = ""

    alert_type: str
    service_name: str
    error_message: str
    metrics: dict[str, Any]  # supports float lists (time-series) and str lists (timestamps)
    logs_snippet: str
    time_of_day: str
    related_alerts: list[str]
    service_dependencies: list[str]
    recent_deployments: list[dict]

    # Cascading failure fields
    new_alert: str = ""  # injected when a cascade is triggered


class TriageAction(BaseModel):
    severity: str
    team: str
    escalate: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"P0", "P1", "P2", "P3", "P4"}
        if v not in valid:
            raise ValueError(f"severity must be one of {valid}")
        return v

    @field_validator("team")
    @classmethod
    def validate_team(cls, v: str) -> str:
        valid = {"backend", "frontend", "infra", "database", "security", "network"}
        if v not in valid:
            raise ValueError(f"team must be one of {valid}")
        return v


class LearningSignal(BaseModel):
    dimension: str  # "severity", "routing", "escalation", etc.
    correct: bool
    reason: str
    improvement_hint: str = ""


class TriageReward(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=0.35)
    routing_score: float = Field(ge=0.0, le=0.30)
    escalation_score: float = Field(ge=0.0, le=0.15)
    reasoning_score: float = Field(ge=0.0, le=0.10)
    calibration_score: float = Field(ge=0.0, le=0.10)
    cascade_penalty: float = Field(ge=-1.0, le=0.0, default=0.0)
    false_positive_bonus: float = Field(ge=0.0, le=0.10, default=0.0)
    trend_bonus: float = Field(ge=0.0, le=0.05, default=0.0)
    adaptation_bonus: float = Field(ge=0.0, le=0.05, default=0.0)
    feedback: str
    # NEW: Learning signals for agent improvement
    learning_signals: list[LearningSignal] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
