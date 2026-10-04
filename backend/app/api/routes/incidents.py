from fastapi import APIRouter, HTTPException

from app.api.dependencies import incidents
from app.models.incident import Incident


router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[Incident])
async def list_incidents():
    return await incidents.list()


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    incident = await incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}/resolve", response_model=Incident)
async def resolve_incident(incident_id: str):
    incident = await incidents.resolve(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
