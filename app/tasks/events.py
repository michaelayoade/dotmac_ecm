import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.events.process_event", ignore_result=True)
def process_event(
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    document_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """Central fan-out task for ECM events.

    Dispatches to notification, webhook, and search-index sub-tasks.
    Each fan-out is wrapped so one failure doesn't block others.
    """
    event_data = {
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_id": actor_id,
        "document_id": document_id,
        "payload": payload or {},
    }
    logger.info("Processing event %s for %s/%s", event_type, entity_type, entity_id)

    _fanout_notifications(event_data)
    _fanout_webhooks(event_data)
    _fanout_search(event_data)


def _fanout_notifications(event_data: dict) -> None:
    try:
        from app.tasks.notifications import dispatch_notifications

        dispatch_notifications.delay(**event_data)
    except Exception as e:
        logger.exception("Failed to fan-out notifications: %s", e)


def _fanout_webhooks(event_data: dict) -> None:
    try:
        from app.tasks.webhooks import deliver_webhooks

        deliver_webhooks.delay(**event_data)
    except Exception as e:
        logger.exception("Failed to fan-out webhooks: %s", e)


def _fanout_search(event_data: dict) -> None:
    try:
        from app.tasks.search import update_search_index

        update_search_index.delay(
            document_id=event_data.get("document_id"),
            event_type=event_data["event_type"],
        )
    except Exception as e:
        logger.exception("Failed to fan-out search index update: %s", e)
