import asyncio

from fastapi import APIRouter, HTTPException

from app.api.dependencies import analyzer, detector, notifier, prometheus
from app.models.integration import AIConnection, DecisionModelConnection, PrometheusConnection, SlackConnection


router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("")
async def integrations():
    return {
        "ai": {
            "configured": analyzer.configured,
            "provider": analyzer.provider,
            "model": analyzer.model,
        },
        "decision_model": {
            "configured": detector.configured,
            "provider": "openrouter",
            "model": detector.model,
        },
        "slack": {"configured": bool(notifier.webhook_url)},
        "prometheus": {
            "configured": prometheus.configured,
            "url": prometheus.base_url,
            "auth_type": prometheus.auth_type,
            "service_name": prometheus.service_name,
        },
    }


@router.post("/decision-model")
async def connect_decision_model(connection: DecisionModelConnection):
    try:
        await asyncio.to_thread(
            detector.test_and_configure, connection.api_key, connection.model
        )
        return {
            "configured": True,
            "provider": "openrouter",
            "model": detector.model,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Decision model connection failed: {exc}") from exc


@router.post("/ai")
async def connect_ai(connection: AIConnection):
    try:
        await analyzer.test_and_configure(
            connection.provider, connection.api_key, connection.model
        )
        return {
            "configured": True,
            "provider": analyzer.provider,
            "model": analyzer.model,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AI provider connection failed: {exc}") from exc


@router.post("/prometheus")
async def connect_prometheus(connection: PrometheusConnection):
    try:
        targets = await prometheus.test_and_configure(connection)
        return {
            "configured": True,
            "url": prometheus.base_url,
            "auth_type": prometheus.auth_type,
            "service_name": prometheus.service_name,
            "targets": targets,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Prometheus connection failed: {exc}") from exc


@router.post("/slack")
async def connect_slack(connection: SlackConnection):
    try:
        await notifier.test_and_configure(connection.webhook_url)
        return {"configured": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Slack connection failed: {exc}") from exc

