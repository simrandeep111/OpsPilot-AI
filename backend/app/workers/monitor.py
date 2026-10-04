import asyncio
import logging


logger = logging.getLogger(__name__)


async def monitor_forever(monitoring, interval_seconds: int) -> None:
    while True:
        try:
            await monitoring.run_all()
        except Exception as exc:
            logger.error("Prometheus monitoring failed: %s", exc)
        await asyncio.sleep(interval_seconds)
