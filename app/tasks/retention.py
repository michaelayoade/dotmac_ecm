import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.retention.check_retention_expiry", ignore_result=True)
def check_retention_expiry() -> None:
    """Periodic task to find pending retentions past their expiry date.

    Updates disposition_status from 'pending' to 'eligible' and publishes
    retention.expired events for each.
    """
    from app.db import SessionLocal
    from app.models.ecm import DispositionStatus, DocumentRetention
    from app.services.event import EventType, publish_event

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired = (
            db.query(DocumentRetention)
            .filter(
                DocumentRetention.disposition_status == DispositionStatus.pending,
                DocumentRetention.retention_expires_at <= now,
                DocumentRetention.is_active.is_(True),
            )
            .all()
        )

        count = 0
        for retention in expired:
            try:
                retention.disposition_status = DispositionStatus.eligible
                db.commit()
                db.refresh(retention)
                publish_event(
                    EventType.retention_expired,
                    entity_type="document_retention",
                    entity_id=str(retention.id),
                    document_id=str(retention.document_id),
                )
                count += 1
            except Exception as e:
                db.rollback()
                logger.warning("Failed to expire retention %s: %s", retention.id, e)

        logger.info("Marked %d retentions as eligible", count)
    except Exception as e:
        logger.exception("Failed to check retention expiry: %s", e)
    finally:
        db.close()
