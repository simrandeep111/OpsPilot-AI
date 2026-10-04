import asyncio
import logging
from datetime import datetime, timezone

from app.models.incident import Incident
from app.models.metric import MetricSnapshot
from app.intelligence.llm.analyzer import Analysis


logger = logging.getLogger("uvicorn.error")


class MonitoringService:
    def __init__(self, settings, detector, analyzer, incidents, notifier, metrics_source):
        self.settings = settings
        self.detector = detector
        self.analyzer = analyzer
        self.incidents = incidents
        self.notifier = notifier
        self.metrics_source = metrics_source
        self.latest: dict[str, MetricSnapshot] = {}
        self._abnormal_checks: dict[str, int] = {}

    async def collect_all(self) -> list[MetricSnapshot]:
        snapshots = await self.metrics_source.metric_snapshots()
        self.latest.update({snapshot.service: snapshot for snapshot in snapshots})
        return snapshots

    async def analyze(self, metrics: MetricSnapshot) -> Incident | None:
        self.latest[metrics.service] = metrics
        source_context = (
            self.metrics_source.context_for(metrics)
            if self.metrics_source and self.metrics_source.configured
            else {}
        )
        try:
            decision = await asyncio.to_thread(
                self.detector.detect, metrics, source_context
            )
        except Exception as exc:
            self._abnormal_checks.pop(metrics.service, None)
            logger.warning("Jev detection failed; skipping incident decision: %s", exc)
            return None
        logger.info(
            "Jev decision: probability=%.2f type=%s severity=%s",
            decision.incident_probability,
            decision.problem_type,
            decision.severity,
        )

        abnormal = (
            decision.incident_probability >= self.settings.jev_incident_probability
            and decision.problem_type != "healthy"
        )
        if not abnormal:
            self._abnormal_checks.pop(metrics.service, None)
            return None

        consecutive = self._abnormal_checks.get(metrics.service, 0) + 1
        self._abnormal_checks[metrics.service] = consecutive
        if consecutive < 2:
            return None

        try:
            analysis = await self.analyzer.analyze(
                metrics, decision.problem_type, decision.severity, source_context=source_context
            )
        except Exception as exc:
            logger.warning("AI analysis failed; using fallback: %s", exc)
            analysis = Analysis(
                likely_cause=f"Metrics indicate {decision.problem_type.replace('_', ' ')}.",
                recommended_action="Inspect the service, recent deployments, and traffic changes.",
                source="fallback (AI provider request failed)",
                affected_resources=[],
            )
        incident = Incident(
            service=metrics.service,
            problem_type=decision.problem_type,
            severity=decision.severity,
            incident_probability=decision.incident_probability,
            classification_confidence=decision.problem_confidence,
            metrics=metrics,
            likely_cause=analysis.likely_cause,
            recommended_action=analysis.recommended_action,
            analysis_source=analysis.source,
            affected_resources=analysis.affected_resources,
            source_context=source_context,
            jev_answers=decision.answers,
            updated_at=datetime.now(timezone.utc),
        )
        saved, created = await self.incidents.save(incident)
        if created:
            try:
                await self.notifier.send_incident(saved)
            except Exception as exc:
                logger.warning("Slack notification failed: %s", exc)
        return saved

    async def run_all(self) -> list[Incident]:
        results = await asyncio.gather(
            *(self.analyze(snapshot) for snapshot in await self.collect_all())
        )
        return [incident for incident in results if incident]
