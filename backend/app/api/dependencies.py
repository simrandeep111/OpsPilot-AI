from app.core.config import settings
from app.integrations.slack.client import SlackNotifier
from app.integrations.prometheus.client import PrometheusIntegration
from app.intelligence.jev.detector import JevDetector
from app.intelligence.llm.analyzer import AIAnalyzer
from app.services.incident_service import IncidentService
from app.services.monitoring_service import MonitoringService


detector = JevDetector(settings.openrouter_api_key, settings.jev_model)
analyzer = AIAnalyzer(settings.ai_provider, settings.ai_api_key, settings.ai_model)
incidents = IncidentService()
notifier = SlackNotifier(settings.slack_webhook_url)
prometheus = PrometheusIntegration(
    settings.prometheus_url,
    settings.prometheus_auth_type,
    settings.prometheus_username,
    settings.prometheus_password,
    settings.prometheus_token,
    settings.prometheus_service_name,
    settings.prometheus_allow_private,
)
monitoring = MonitoringService(settings, detector, analyzer, incidents, notifier, prometheus)
