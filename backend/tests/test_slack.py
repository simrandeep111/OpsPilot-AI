import unittest
import json

import httpx

from app.integrations.slack.client import SlackNotifier
from app.models.incident import Incident
from app.models.metric import MetricSnapshot, MetricTrend


class SlackNotifierTest(unittest.IsolatedAsyncioTestCase):
    async def test_connection_sends_message_and_updates_webhook(self):
        async def handler(request):
            self.assertEqual(request.url.host, "hooks.slack.com")
            self.assertIn("connection test", request.content.decode())
            return httpx.Response(200, text="ok")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            notifier = SlackNotifier(None, client)
            webhook = "https://hooks.slack.com/services/test/webhook/value"
            await notifier.test_and_configure(webhook)
        self.assertEqual(notifier.webhook_url, webhook)

    async def test_incident_uses_structured_blocks_without_emoji(self):
        async def handler(request):
            payload = json.loads(request.content)
            rendered = json.dumps(payload)
            self.assertEqual(len(payload["blocks"]), 7)
            self.assertIn("Evidence", rendered)
            self.assertIn("Jev Detection", rendered)
            self.assertIn("AI Analysis", rendered)
            self.assertNotIn(":rotating_light:", rendered)
            return httpx.Response(200, text="ok")

        incident = Incident(
            service="ec2:test-instance",
            problem_type="error_spike",
            severity="high",
            incident_probability=0.15,
            classification_confidence=0.71,
            metrics=MetricSnapshot(
                service="ec2:test-instance", resource_type="ec2", resource_id="i-test123",
                cpu_percent=98, memory_percent=92, latency_ms=2500, error_rate_percent=15,
                trends={"cpu_percent": MetricTrend(
                    baseline=50, average=65, peak=98, rate_of_change_per_minute=1.1,
                    deviation_from_baseline=48, deviation_percent=96,
                    sustained_direction="above", sustained_duration_minutes=20,
                    sample_count=12, window_minutes=60,
                )},
            ),
            likely_cause="Resource saturation is causing errors.",
            recommended_action="Scale the service and inspect recent deployments.",
            analysis_source="groq:qwen/qwen3.8-27b",
            affected_resources=["i-test123"],
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await SlackNotifier("https://hooks.slack.com/services/test/value/key", client).send_incident(incident)


if __name__ == "__main__":
    unittest.main()
