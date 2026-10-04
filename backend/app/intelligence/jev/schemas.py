from dataclasses import dataclass


@dataclass(frozen=True)
class JevDecision:
    incident_probability: float
    problem_type: str
    problem_confidence: float
    severity: str
    severity_confidence: float
    answers: dict
