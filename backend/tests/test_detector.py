import unittest

from app.intelligence.jev.detector import OPENROUTER_DECISIONS_URL, JevDetector
from app.models.metric import MetricSnapshot, MetricTrend


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "answers": {
                "incident": {"type": "noul", "noul": 0.91},
                "problem_type": {"type": "choice", "choice": "cpu_saturation", "confidence": 0.94},
                "severity": {"type": "choice", "choice": "high", "confidence": 0.88},
            }
        }


class FakeClient:
    def post(self, url, headers, json):
        self.url = url
        self.headers = headers
        self.payload = json
        return FakeResponse()


class DetectorTest(unittest.TestCase):
    def test_configures_openrouter_decision_model_after_successful_test(self):
        client = FakeClient()
        detector = JevDetector(None, client=client)

        detector.test_and_configure("test-api-key", "~typesafe/jev-latest")

        self.assertTrue(detector.configured)
        self.assertEqual(detector.model, "~typesafe/jev-latest")
        self.assertEqual(client.headers["Authorization"], "Bearer test-api-key")
        self.assertIn("ready", client.payload["questions"])

    def test_maps_jev_answers(self):
        client = FakeClient()
        decision = JevDetector("test-key", client=client).detect(
            MetricSnapshot(
                service="payments", cpu_percent=98, memory_percent=70,
                latency_ms=2400, error_rate_percent=18,
                trends={"cpu_percent": MetricTrend(
                    baseline=45, average=60, peak=98, rate_of_change_per_minute=1.2,
                    deviation_from_baseline=53, deviation_percent=117.8,
                    sustained_direction="above", sustained_duration_minutes=20,
                    sample_count=12, window_minutes=60,
                )},
            ),
            {"metrics_source": "prometheus", "service": "payments"},
        )
        self.assertEqual(decision.problem_type, "cpu_saturation")
        self.assertEqual(decision.severity, "high")
        self.assertAlmostEqual(decision.incident_probability, 0.91)
        self.assertEqual(client.url, OPENROUTER_DECISIONS_URL)
        self.assertEqual(client.headers["Authorization"], "Bearer test-key")
        self.assertEqual(client.payload["state"]["metrics"]["cpu_percent"], 98)


if __name__ == "__main__":
    unittest.main()
