import asyncio
import base64
import ipaddress
import math
import socket
from datetime import datetime, timedelta, timezone
from statistics import fmean, median
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models.integration import PrometheusConnection
from app.models.metric import MetricSnapshot, MetricTrend


PROMQL_QUERIES = {
    "cpu_percent": "100 - (avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
    "memory_percent": "(1 - (sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))) * 100",
    "latency_ms": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
    "error_rate_percent": "(sum(rate(http_requests_total{status=~\"5..\"}[5m])) / clamp_min(sum(rate(http_requests_total[5m])), 0.000001)) * 100",
    "request_rate": "sum(rate(http_requests_total[5m]))",
    "targets_up": "sum(up)",
}


class PrometheusIntegration:
    def __init__(
        self,
        base_url: str | None = None,
        auth_type: str = "none",
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        service_name: str = "prometheus",
        allow_private: bool = False,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.auth_type = auth_type
        self.username = username
        self.password = password
        self.token = token
        self.service_name = service_name
        self.allow_private = allow_private
        self.client = client
        self._validated_url: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    @staticmethod
    def _is_private(address: str) -> bool:
        value = ipaddress.ip_address(address)
        return any((value.is_private, value.is_loopback, value.is_link_local, value.is_reserved, value.is_unspecified))

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Prometheus URL must use http or https")
        if self.allow_private:
            return
        hostname = parsed.hostname.lower()
        if hostname == "localhost" or hostname.endswith(".local"):
            raise ValueError("Private Prometheus URLs are disabled")
        try:
            if self._is_private(hostname):
                raise ValueError("Private Prometheus URLs are disabled")
            return
        except ValueError as exc:
            if "disabled" in str(exc):
                raise
        if self.client is None:
            # ponytail: DNS can change after validation; enforce outbound network policy for stronger SSRF isolation.
            try:
                addresses = {
                    item[4][0]
                    for item in socket.getaddrinfo(
                        hostname,
                        parsed.port or (443 if parsed.scheme == "https" else 80),
                        type=socket.SOCK_STREAM,
                    )
                }
            except socket.gaierror as exc:
                raise ValueError("Prometheus hostname could not be resolved") from exc
            if any(self._is_private(address) for address in addresses):
                raise ValueError("Private Prometheus URLs are disabled")

    @staticmethod
    def _headers(auth_type: str, username: str | None, password: str | None, token: str | None) -> dict[str, str]:
        if auth_type not in {"none", "basic", "bearer"}:
            raise ValueError("Unsupported Prometheus authentication type")
        if auth_type == "basic":
            if not username or not password:
                raise ValueError("Prometheus username and password are required")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        if auth_type == "bearer":
            if not token:
                raise ValueError("Prometheus bearer token is required")
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def _get(self, path: str, params: dict[str, Any], *, connection: PrometheusConnection | None = None) -> dict:
        base_url = str(connection.url).rstrip("/") if connection else self.base_url
        auth_type = connection.auth_type if connection else self.auth_type
        username = connection.username if connection else self.username
        password = connection.password if connection else self.password
        token = connection.token if connection else self.token
        if not base_url:
            raise RuntimeError("Prometheus is not configured")
        if self._validated_url != base_url:
            await asyncio.to_thread(self._validate_url, base_url)
            self._validated_url = base_url
        headers = self._headers(auth_type, username, password, token)
        if self.client:
            response = await self.client.get(f"{base_url}{path}", params=params, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{base_url}{path}", params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("error", "Prometheus query failed"))
        return payload

    async def test_and_configure(self, connection: PrometheusConnection) -> int:
        payload = await self._get("/api/v1/query", {"query": "up"}, connection=connection)
        self.base_url = str(connection.url).rstrip("/")
        self.auth_type = connection.auth_type
        self.username = connection.username
        self.password = connection.password
        self.token = connection.token
        self.service_name = connection.service_name
        return len(payload.get("data", {}).get("result", []))

    @staticmethod
    def _points(payload: dict) -> list[tuple[datetime, float]]:
        combined: dict[datetime, list[float]] = {}
        for series in payload.get("data", {}).get("result", []):
            samples = series.get("values") or ([series["value"]] if series.get("value") else [])
            for timestamp, raw_value in samples:
                value = float(raw_value)
                if math.isfinite(value):
                    observed_at = datetime.fromtimestamp(float(timestamp), timezone.utc)
                    combined.setdefault(observed_at, []).append(value)
        return sorted((timestamp, float(fmean(values))) for timestamp, values in combined.items())

    @staticmethod
    def _trend(history: list[tuple[datetime, float]]) -> MetricTrend | None:
        if not history:
            return None
        values = [value for _, value in history]
        baseline = float(median(values))
        latest = values[-1]
        if len(history) > 1:
            gaps = [(right[0] - left[0]).total_seconds() / 60 for left, right in zip(history, history[1:])]
            interval = float(median(gaps))
            elapsed = (history[-1][0] - history[0][0]).total_seconds() / 60
        else:
            interval = elapsed = 0.0
        direction = "stable" if latest == baseline else "above" if latest > baseline else "below"
        sustained = 0
        if direction != "stable":
            for value in reversed(values):
                if (direction == "above" and value <= baseline) or (direction == "below" and value >= baseline):
                    break
                sustained += 1
        deviation = latest - baseline
        return MetricTrend(
            baseline=baseline,
            average=float(fmean(values)),
            peak=max(values),
            rate_of_change_per_minute=(latest - values[0]) / elapsed if elapsed else 0,
            deviation_from_baseline=deviation,
            deviation_percent=100 * deviation / baseline if baseline else None,
            sustained_direction=direction,
            sustained_duration_minutes=sustained * interval,
            sample_count=len(values),
            window_minutes=elapsed + interval,
        )

    async def metric_snapshots(self) -> list[MetricSnapshot]:
        if not self.configured:
            return []
        end = datetime.now(timezone.utc)
        histories = {}
        for name, query in PROMQL_QUERIES.items():
            payload = await self._get(
                "/api/v1/query_range",
                {"query": query, "start": (end - timedelta(minutes=60)).timestamp(), "end": end.timestamp(), "step": 300},
            )
            histories[name] = self._points(payload)
        if not any(histories.values()):
            return []
        trends = {
            name: trend
            for name, history in histories.items()
            if name != "targets_up" and (trend := self._trend(history)) is not None
        }
        latest = {name: history[-1][1] for name, history in histories.items() if history}
        return [MetricSnapshot(
            service=self.service_name,
            resource_type="prometheus",
            resource_id=self.service_name,
            cpu_percent=latest.get("cpu_percent"),
            memory_percent=latest.get("memory_percent"),
            latency_ms=latest.get("latency_ms"),
            error_rate_percent=latest.get("error_rate_percent"),
            request_rate=latest.get("request_rate"),
            baseline_cpu_percent=trends.get("cpu_percent").baseline if "cpu_percent" in trends else None,
            baseline_memory_percent=trends.get("memory_percent").baseline if "memory_percent" in trends else None,
            baseline_latency_ms=trends.get("latency_ms").baseline if "latency_ms" in trends else None,
            baseline_error_rate_percent=trends.get("error_rate_percent").baseline if "error_rate_percent" in trends else None,
            baseline_request_rate=trends.get("request_rate").baseline if "request_rate" in trends else None,
            extra_metrics={"targets_up": latest["targets_up"]} if "targets_up" in latest else {},
            trends=trends,
        )]

    def context_for(self, metrics: MetricSnapshot) -> dict:
        return {
            "metrics_source": "prometheus",
            "service": metrics.service,
            "resource_id": metrics.resource_id,
        }
