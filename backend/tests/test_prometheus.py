import unittest
from datetime import datetime, timezone

import httpx

from app.integrations.prometheus.client import PROMQL_QUERIES, PrometheusIntegration
from app.models.integration import PrometheusConnection


class PrometheusIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_connection_supports_bearer_auth(self):
        async def handler(request):
            self.assertEqual(request.url.path, "/api/v1/query")
            self.assertEqual(request.url.params["query"], "up")
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            return httpx.Response(200, json={
                "status": "success",
                "data": {"resultType": "vector", "result": [{"metric": {"job": "api"}, "value": [1, "1"]}]},
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            prometheus = PrometheusIntegration(client=client)
            targets = await prometheus.test_and_configure(PrometheusConnection(
                url="https://prometheus.example.com",
                auth_type="bearer",
                token="test-token",
                service_name="payment-api",
            ))
        self.assertEqual(targets, 1)
        self.assertTrue(prometheus.configured)
        self.assertEqual(prometheus.service_name, "payment-api")

    async def test_collects_promql_history_and_builds_trends(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()

        async def handler(request):
            query = request.url.params["query"]
            values = {
                PROMQL_QUERIES["cpu_percent"]: [10, 20, 30, 40],
                PROMQL_QUERIES["memory_percent"]: [50, 55, 60, 65],
                PROMQL_QUERIES["latency_ms"]: [100, 150, 200, 800],
                PROMQL_QUERIES["error_rate_percent"]: [1, 2, 4, 12],
                PROMQL_QUERIES["request_rate"]: [20, 25, 30, 35],
                PROMQL_QUERIES["targets_up"]: [2, 2, 2, 2],
            }[query]
            return httpx.Response(200, json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [{"metric": {}, "values": [[start + index * 300, str(value)] for index, value in enumerate(values)]}],
                },
            })

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            prometheus = PrometheusIntegration(
                "https://prometheus.example.com", service_name="payment-api", client=client
            )
            snapshot = (await prometheus.metric_snapshots())[0]
        self.assertEqual(snapshot.resource_type, "prometheus")
        self.assertEqual(snapshot.cpu_percent, 40)
        self.assertEqual(snapshot.latency_ms, 800)
        self.assertEqual(snapshot.extra_metrics["targets_up"], 2)
        self.assertEqual(snapshot.trends["cpu_percent"].baseline, 25)
        self.assertEqual(snapshot.trends["cpu_percent"].window_minutes, 20)

    async def test_blocks_private_urls_by_default(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
            prometheus = PrometheusIntegration(client=client)
            with self.assertRaisesRegex(ValueError, "Private Prometheus URLs"):
                await prometheus.test_and_configure(PrometheusConnection(url="http://127.0.0.1:9090"))


if __name__ == "__main__":
    unittest.main()
