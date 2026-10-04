from typing import Any

import httpx

from app.intelligence.jev.schemas import JevDecision
from app.models.metric import MetricSnapshot


OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

QUESTIONS = {
    "incident": {
        "type": "noul",
        "instructions": "Is an infrastructure incident emerging or active based on sustained worsening trends?",
        "criteria": {
            "true": "The state shows a sustained or worsening service-impacting abnormality.",
            "false": "The service is healthy, stable, transiently noisy, or recovering.",
        },
    },
    "problem_type": {
        "type": "choice",
        "instructions": "What type of infrastructure problem is most likely?",
        "criteria": {
            "cpu_saturation": "CPU usage is excessively high",
            "memory_pressure": "Memory usage is excessively high",
            "latency_spike": "Request latency is abnormally high",
            "error_spike": "Application error rate is abnormally high",
            "traffic_spike": "Incoming request traffic increased significantly",
            "healthy": "System behavior appears normal",
        },
    },
    "severity": {
        "type": "choice",
        "instructions": "How severe is the current system state?",
        "criteria": {
            "low": "Minor abnormality",
            "medium": "Noticeable degradation",
            "high": "Serious degradation requiring attention",
            "critical": "Major production incident",
        },
    },
}


def build_jev_state(metrics, aws_context=None):
    return {
        "metrics": metrics.model_dump(mode="json"),
        "aws_context": aws_context or {},
    }


class JevDetector:
    def __init__(
        self,
        api_key: str | None,
        model: str = "typesafe/jev-1.13",
        client: Any | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=10)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def test_and_configure(self, api_key: str, model: str) -> None:
        response = self.client.post(
            OPENROUTER_DECISIONS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "state": "OpsPilot decision model connection test",
                "questions": {
                    "ready": {
                        "type": "noul",
                        "instructions": "Is this a connection test?",
                        "criteria": {"true": "This is a connection test", "false": "This is not a connection test"},
                    }
                },
            },
        )
        response.raise_for_status()
        self.api_key = api_key
        self.model = model

    def detect(
        self,
        metrics: MetricSnapshot,
        aws_context: dict | None = None,
    ) -> JevDecision:
        if not self.configured:
            raise RuntimeError("OPENROUTER_API_KEY is required for Jev decisions")

        response = self.client.post(
            OPENROUTER_DECISIONS_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "state": build_jev_state(metrics, aws_context),
                "questions": QUESTIONS,
            },
        )
        response.raise_for_status()
        answers = response.json()["answers"]
        problem = answers["problem_type"]
        severity = answers["severity"]
        return JevDecision(
            incident_probability=float(answers["incident"]["noul"]),
            problem_type=str(problem["choice"]),
            problem_confidence=float(problem["confidence"]),
            severity=str(severity["choice"]),
            severity_confidence=float(severity["confidence"]),
            answers=answers,
        )
