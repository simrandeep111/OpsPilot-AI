from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "monitoring": settings.monitoring_enabled,
        "metrics_source": "aws_cloudwatch",
        "jev_model": settings.jev_model,
        "jev_configured": bool(settings.openrouter_api_key),
        "ai_configured": bool(settings.ai_api_key),
        "slack_configured": bool(settings.slack_webhook_url),
    }
