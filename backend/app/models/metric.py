from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MetricTrend(BaseModel):
    baseline: float
    average: float
    peak: float
    rate_of_change_per_minute: float
    deviation_from_baseline: float
    deviation_percent: float | None = None
    sustained_direction: str
    sustained_duration_minutes: float
    sample_count: int = Field(ge=1)
    window_minutes: float = Field(ge=0)


class MetricSnapshot(BaseModel):
    service: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_.:/-]+$")
    resource_type: str = "custom"
    resource_id: str | None = None
    cpu_percent: float | None = Field(default=None, ge=0)
    memory_percent: float | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0)
    error_rate_percent: float | None = Field(default=None, ge=0)
    request_rate: float | None = Field(default=None, ge=0)
    baseline_cpu_percent: float | None = Field(default=None, ge=0)
    baseline_memory_percent: float | None = Field(default=None, ge=0)
    baseline_latency_ms: float | None = Field(default=None, ge=0)
    baseline_error_rate_percent: float | None = Field(default=None, ge=0)
    baseline_request_rate: float | None = Field(default=None, ge=0)
    extra_metrics: dict[str, float] = Field(default_factory=dict)
    trends: dict[str, MetricTrend] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def as_context(self) -> str:
        values = [
            f"Resource: {self.service}",
            f"Resource type: {self.resource_type}",
            f"Observed at: {self.observed_at.isoformat()}",
        ]
        current = {
            "CPU (%)": self.cpu_percent,
            "Memory (%)": self.memory_percent,
            "P95 latency (ms)": self.latency_ms,
            "Error rate (%)": self.error_rate_percent,
            "Request rate (/second)": self.request_rate,
        }
        values.extend(f"{name}: {value:.2f}" for name, value in current.items() if value is not None)
        baselines = {
            "Normal CPU": self.baseline_cpu_percent,
            "Normal memory": self.baseline_memory_percent,
            "Normal P95 latency": self.baseline_latency_ms,
            "Normal error rate": self.baseline_error_rate_percent,
            "Normal request rate": self.baseline_request_rate,
        }
        values.extend(f"{name}: {value:.2f}" for name, value in baselines.items() if value is not None)
        values.extend(f"{name}: {value:.2f}" for name, value in self.extra_metrics.items())
        for name, trend in self.trends.items():
            deviation = (
                f"{trend.deviation_percent:+.2f}%"
                if trend.deviation_percent is not None
                else f"{trend.deviation_from_baseline:+.2f}"
            )
            values.append(
                f"{name} trend ({trend.window_minutes:.0f} min, {trend.sample_count} samples): "
                f"baseline={trend.baseline:.2f}, average={trend.average:.2f}, "
                f"peak={trend.peak:.2f}, change/min={trend.rate_of_change_per_minute:+.2f}, "
                f"deviation={deviation}, sustained {trend.sustained_direction}="
                f"{trend.sustained_duration_minutes:.0f} min"
            )
        return "\n".join(values)
