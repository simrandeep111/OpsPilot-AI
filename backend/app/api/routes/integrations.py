import asyncio

from fastapi import APIRouter, HTTPException

from app.api.dependencies import analyzer, aws, detector, notifier
from app.models.integration import AIConnection, AWSConnection, DecisionModelConnection, SlackConnection


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
        "aws": {
            "configured": aws.configured,
            "role_arn": aws.role_arn,
            "regions": aws.regions,
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


@router.post("/aws")
async def connect_aws(connection: AWSConnection):
    try:
        identity = await aws.test_and_configure(connection)
        return {"configured": True, "regions": aws.regions, **identity}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AWS connection failed: {exc}") from exc


@router.post("/slack")
async def connect_slack(connection: SlackConnection):
    try:
        await notifier.test_and_configure(connection.webhook_url)
        return {"configured": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Slack connection failed: {exc}") from exc


@router.get("/aws/inventory")
async def aws_inventory():
    if not aws.configured:
        raise HTTPException(status_code=400, detail="AWS is not configured")
    try:
        return await aws.inventory()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AWS inventory failed: {exc}") from exc
