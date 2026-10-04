import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import monitoring
from app.intelligence.jev.schemas import JevDecision
from app.intelligence.llm.analyzer import Analysis
from app.main import app


class FakeDetector:
    def detect(self, metrics, source_context=None):
        return JevDecision(0.91, "cpu_saturation", 0.94, "high", 0.88, {})


class FakeAnalyzer:
    async def analyze(self, metrics, problem_type, severity, source_context=None):
        return Analysis("CPU demand exceeds capacity.", "Increase replicas.", "test", ["i-123"])


class ApiTest(unittest.TestCase):
    def test_local_frontend_is_allowed_by_cors(self):
        with TestClient(app) as client:
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")

    def test_mock_metrics_flow_to_incident_api(self):
        detector, analyzer = monitoring.detector, monitoring.analyzer
        monitoring.detector, monitoring.analyzer = FakeDetector(), FakeAnalyzer()
        try:
            with TestClient(app) as client:
                payload = {
                    "service": "api-test",
                    "cpu_percent": 98,
                    "memory_percent": 70,
                    "latency_ms": 2400,
                    "error_rate_percent": 18,
                    "request_rate": 120,
                }
                first = client.post("/api/metrics/analyze", json=payload)
                response = client.post("/api/metrics/analyze", json=payload)
                self.assertIsNone(first.json()["incident"])
                self.assertEqual(response.status_code, 200)
                incident = response.json()["incident"]
                self.assertEqual(incident["problem_type"], "cpu_saturation")
                self.assertEqual(incident["severity"], "high")
                self.assertTrue(client.get("/api/incidents").json())
                self.assertEqual(client.get("/api/metrics/latest").json()[0]["cpu_percent"], 98)
        finally:
            monitoring.detector, monitoring.analyzer = detector, analyzer


if __name__ == "__main__":
    unittest.main()
