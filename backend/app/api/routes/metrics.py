from fastapi import APIRouter, HTTPException

from app.api.dependencies import monitoring
from app.models.metric import MetricSnapshot


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/latest", response_model=list[MetricSnapshot])
async def latest_metrics():
    return list(monitoring.latest.values())


@router.post("/analyze")
async def analyze_metrics(metrics: MetricSnapshot):
    incident = await monitoring.analyze(metrics)
    return {"incident": incident}


@router.post("/collect")
async def collect_and_analyze():
    try:
        incidents = await monitoring.run_all()
        return {"incidents": incidents}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
