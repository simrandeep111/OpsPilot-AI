from app.core.config import settings
from app.integrations.slack.client import SlackNotifier
from app.integrations.aws.client import AWSIntegration
from app.intelligence.jev.detector import JevDetector
from app.intelligence.llm.analyzer import AIAnalyzer
from app.services.incident_service import IncidentService
from app.services.monitoring_service import MonitoringService


detector = JevDetector(settings.openrouter_api_key, settings.jev_model)
analyzer = AIAnalyzer(settings.ai_provider, settings.ai_api_key, settings.ai_model)
incidents = IncidentService()
notifier = SlackNotifier(settings.slack_webhook_url)
aws = AWSIntegration(settings.aws_role_arn, settings.aws_external_id, settings.aws_regions)
monitoring = MonitoringService(settings, detector, analyzer, incidents, notifier, aws)
