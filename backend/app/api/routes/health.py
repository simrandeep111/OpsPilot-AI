from fastapi import APIRouter

from app.api.dependencies import analyzer, detector, notifier, prometheus
from app.core.config import settings


router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "monitoring": settings.monitoring_enabled,
        "metrics_source": "prometheus",
        "prometheus_configured": prometheus.configured,
        "jev_model": settings.jev_model,
        "jev_configured": detector.configured,
        "ai_configured": analyzer.configured,
        "slack_configured": bool(notifier.webhook_url),
    }
