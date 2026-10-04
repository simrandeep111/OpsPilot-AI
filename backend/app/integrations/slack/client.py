import httpx

from app.models.incident import Incident


class SlackNotifier:
    def __init__(self, webhook_url: str | None, client: httpx.AsyncClient | None = None):
        self.webhook_url = webhook_url
        self.client = client

    async def _post(self, webhook_url: str, payload: dict):
        if self.client:
            return await self.client.post(webhook_url, json=payload)
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.post(webhook_url, json=payload)

    async def test_and_configure(self, webhook_url: str) -> None:
        response = await self._post(
            webhook_url, {"text": "OpsPilot Slack connection test successful."}
        )
        response.raise_for_status()
        self.webhook_url = webhook_url

    async def send_incident(self, incident: Incident) -> bool:
        if not self.webhook_url:
            return False
        title = incident.problem_type.replace("_", " ").title()
        detected = incident.created_at.strftime("%b %d, %Y at %H:%M UTC")
        metrics = incident.metrics
        evidence = []
        for label, value, suffix in (
            ("CPU", metrics.cpu_percent, "%"),
            ("Memory", metrics.memory_percent, "%"),
            ("P95 latency", metrics.latency_ms, " ms"),
            ("Error rate", metrics.error_rate_percent, "%"),
            ("Request rate", metrics.request_rate, "/second"),
        ):
            if value is not None:
                evidence.append(f"• *{label}:* {value:.1f}{suffix}")
        for name, trend in metrics.trends.items():
            deviation = (
                f"{trend.deviation_percent:+.1f}%"
                if trend.deviation_percent is not None
                else f"{trend.deviation_from_baseline:+.1f}"
            )
            evidence.append(
                f"• *{name} trend:* baseline {trend.baseline:.1f}, average {trend.average:.1f}, "
                f"peak {trend.peak:.1f}, change {trend.rate_of_change_per_minute:+.2f}/min, "
                f"deviation {deviation}, sustained {trend.sustained_direction} "
                f"{trend.sustained_duration_minutes:.0f} min"
            )

        provider, _, model = incident.analysis_source.partition(":")
        ai_source = f"{provider.title()} · {model}" if model else incident.analysis_source
        affected = ", ".join(incident.affected_resources) or incident.metrics.resource_id or "Not identified"
        fallback = f"{incident.severity.upper()} — {title} on {incident.service}"
        payload = {
            "text": fallback,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": fallback},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Resource*\n`{incident.service}`"},
                        {"type": "mrkdwn", "text": f"*Detected*\n{detected}"},
                        {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident.id}`"},
                        {"type": "mrkdwn", "text": f"*Affected resources*\n{affected}"},
                    ],
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Evidence*\n" + "\n".join(evidence)},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Jev Detection*\n"
                            f"• *Classification:* {title}\n"
                            f"• *Confidence:* {incident.classification_confidence:.1%}\n"
                            f"• *Severity:* {incident.severity.title()}"
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*AI Analysis*\n"
                            f"• *Provider and model:* {ai_source}\n"
                            f"• *Likely cause:* {incident.likely_cause}"
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommended Action*\n{incident.recommended_action}",
                    },
                },
            ],
        }
        response = await self._post(self.webhook_url, payload)
        response.raise_for_status()
        return True
