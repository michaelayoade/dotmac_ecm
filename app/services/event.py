import enum
import logging
import uuid

logger = logging.getLogger(__name__)


class EventType(enum.Enum):
    document_created = "document.created"
    document_updated = "document.updated"
    document_deleted = "document.deleted"
    document_status_changed = "document.status_changed"

    version_created = "version.created"
    version_deleted = "version.deleted"

    document_checked_out = "document.checked_out"
    document_checked_in = "document.checked_in"

    comment_created = "comment.created"
    comment_updated = "comment.updated"
    comment_deleted = "comment.deleted"

    workflow_started = "workflow.started"
    workflow_completed = "workflow.completed"
    workflow_cancelled = "workflow.cancelled"
    workflow_task_created = "workflow.task_created"
    workflow_task_completed = "workflow.task_completed"

    retention_applied = "retention.applied"
    retention_expired = "retention.expired"
    retention_disposed = "retention.disposed"

    legal_hold_created = "legal_hold.created"
    legal_hold_released = "legal_hold.released"
    legal_hold_document_added = "legal_hold.document_added"
    legal_hold_document_removed = "legal_hold.document_removed"

    acl_granted = "acl.granted"
    acl_revoked = "acl.revoked"


def publish_event(
    event_type: EventType,
    entity_type: str,
    entity_id: str | uuid.UUID,
    actor_id: str | uuid.UUID | None = None,
    document_id: str | uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    """Fire-and-forget event publishing.

    Queues a Celery task for fan-out to notifications, webhooks, and search.
    Never raises — logs failures and continues.
    """
    try:
        from app.tasks.events import process_event

        process_event.delay(
            event_type=event_type.value,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_id=str(actor_id) if actor_id else None,
            document_id=str(document_id) if document_id else None,
            payload=payload or {},
        )
        logger.debug(
            "Published event %s for %s/%s", event_type.value, entity_type, entity_id
        )
    except Exception as e:
        logger.exception("Failed to publish event %s: %s", event_type.value, e)
