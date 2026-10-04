import unittest

from app.core.config import Settings
from app.intelligence.jev.schemas import JevDecision
from app.intelligence.llm.analyzer import Analysis
from app.models.metric import MetricSnapshot
from app.services.incident_service import IncidentService
from app.services.monitoring_service import MonitoringService


class FakeDetector:
    def __init__(self, probability=0.91, problem_type="cpu_saturation", severity="medium"):
        self.decision = JevDecision(probability, problem_type, 0.94, severity, 0.88, {})

    def detect(self, metrics, aws_context=None):
        return self.decision


class FakeAnalyzer:
    async def analyze(self, metrics, problem_type, severity, aws_context=None):
        return Analysis("CPU demand exceeds capacity.", "Increase replicas.", "test", ["i-123"])


class FakeNotifier:
    def __init__(self):
        self.sent = 0

    async def send_incident(self, incident):
        self.sent += 1
        return True


class MonitoringTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.notifier = FakeNotifier()
        self.incidents = IncidentService()
        self.monitoring = MonitoringService(
            Settings(), FakeDetector(), FakeAnalyzer(), self.incidents, self.notifier, None
        )

    async def test_two_jev_detections_create_and_deduplicate_incident(self):
        metrics = MetricSnapshot(
            service="payment-api", cpu_percent=98, memory_percent=70,
            latency_ms=2400, error_rate_percent=18,
        )
        first = await self.monitoring.analyze(metrics)
        second = await self.monitoring.analyze(metrics)
        third = await self.monitoring.analyze(metrics)
        self.assertIsNone(first)
        self.assertEqual(second.id, third.id)
        self.assertEqual(second.problem_type, "cpu_saturation")
        self.assertEqual(second.severity, "medium")
        self.assertEqual(self.notifier.sent, 1)

    async def test_static_metric_values_cannot_create_incident(self):
        self.monitoring.detector = FakeDetector(probability=0.1)
        metrics = MetricSnapshot(
            service="payment-api", cpu_percent=100, memory_percent=100,
            latency_ms=10000, error_rate_percent=100,
        )
        self.assertIsNone(await self.monitoring.analyze(metrics))
        self.assertIsNone(await self.monitoring.analyze(metrics))

    async def test_normal_jev_result_resets_consecutive_count(self):
        metrics = MetricSnapshot(service="payment-api", cpu_percent=98)
        self.assertIsNone(await self.monitoring.analyze(metrics))
        self.monitoring.detector = FakeDetector(probability=0.1, problem_type="healthy")
        self.assertIsNone(await self.monitoring.analyze(metrics))
        self.monitoring.detector = FakeDetector()
        self.assertIsNone(await self.monitoring.analyze(metrics))


if __name__ == "__main__":
    unittest.main()
