from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.ingestion.base import BaseScraper, ScrapedRecord
from harvest_edge.models import IngestionLog

RecordProcessor = Callable[[AsyncSession, list[ScrapedRecord]], Awaitable[int]]


class IngestionRunner:
    async def run(
        self,
        session: AsyncSession,
        data_source_id: int,
        scraper: BaseScraper,
        processor: RecordProcessor,
    ) -> int:
        started_at = datetime.now(UTC)
        log = IngestionLog(
            data_source_id=data_source_id,
            scraper_name=type(scraper).__name__,
            status="running",
            started_at=started_at,
            records_processed=0,
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        log_id = log.id

        try:
            records = await scraper.fetch_records()
            processed = await processor(session, records)
            if processed < 0:
                raise ValueError("An ingestion processor cannot report a negative record count")
            log.status = "succeeded"
            log.records_processed = processed
            log.completed_at = datetime.now(UTC)
            await session.commit()
            return processed
        except Exception as exc:
            await session.rollback()
            failed_log = await session.get(IngestionLog, log_id)
            if failed_log is not None:
                failed_log.status = "failed"
                failed_log.completed_at = datetime.now(UTC)
                failed_log.error_payload = {
                    "exception_type": type(exc).__name__,
                    "message": str(exc)[:1000],
                }
                await session.commit()
            raise
