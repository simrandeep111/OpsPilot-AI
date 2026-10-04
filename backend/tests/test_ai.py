import json
import unittest

import httpx

from app.intelligence.llm.analyzer import AIAnalyzer
from app.models.metric import MetricSnapshot


class AIAnalyzerTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_providers_receive_context_and_map_resources(self):
        seen_hosts = []

        async def handler(request):
            seen_hosts.append(request.url.host)
            self.assertIn("payment-api", request.content.decode())
            result = json.dumps({
                "likely_cause": "The service CPU is saturated.",
                "affected_resources": ["payment-api"],
                "recommended_action": "Scale the service to three instances.",
            })
            if request.url.host == "api.openai.com":
                return httpx.Response(200, json={
                    "output": [{"content": [{"type": "output_text", "text": result}]}]
                })
            if request.url.host == "api.anthropic.com":
                return httpx.Response(200, json={"content": [{"type": "text", "text": result}]})
            return httpx.Response(200, json={"choices": [{"message": {"content": result}}]})

        metrics = MetricSnapshot(service="payment-api", cpu_percent=98)
        models = {
            "openai": "gpt-5.6-luna",
            "anthropic": "claude-sonnet-5",
            "groq": "openai/gpt-oss-20b",
        }
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            for provider, model in models.items():
                result = await AIAnalyzer(provider, "test-key-value", model, client).analyze(
                    metrics,
                    "cpu_saturation",
                    "high",
                    {"metrics_source": "prometheus", "service": "payment-api"},
                )
                self.assertEqual(result.affected_resources, ["payment-api"])
                self.assertEqual(result.source, f"{provider}:{model}")

        self.assertEqual(
            seen_hosts,
            ["api.openai.com", "api.anthropic.com", "api.groq.com"],
        )


if __name__ == "__main__":
    unittest.main()
