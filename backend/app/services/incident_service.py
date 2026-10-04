import asyncio
from datetime import datetime, timezone

from app.models.incident import Incident


class IncidentService:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._lock = asyncio.Lock()

    async def save(self, incident: Incident) -> tuple[Incident, bool]:
        async with self._lock:
            for existing in self._incidents.values():
                if (
                    existing.status == "active"
                    and existing.service == incident.service
                    and existing.problem_type == incident.problem_type
                ):
                    updated = incident.model_copy(
                        update={"id": existing.id, "created_at": existing.created_at}
                    )
                    self._incidents[existing.id] = updated
                    return updated, False
            self._incidents[incident.id] = incident
            return incident, True

    async def list(self) -> list[Incident]:
        return sorted(self._incidents.values(), key=lambda item: item.updated_at, reverse=True)

    async def get(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    async def resolve(self, incident_id: str) -> Incident | None:
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                return None
            resolved = incident.model_copy(
                update={"status": "resolved", "updated_at": datetime.now(timezone.utc)}
            )
            self._incidents[incident_id] = resolved
            return resolved
