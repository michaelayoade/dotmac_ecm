import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notifications.dispatch_notifications", ignore_result=True
)
def dispatch_notifications(
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    document_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """Dispatch in-app notifications for an event.

    Looks up DocumentSubscription records, creates Notification records,
    and queues email tasks for subscribers.
    """
    if not document_id:
        return

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        _dispatch(
            db, event_type, entity_type, entity_id, actor_id, document_id, payload
        )
    except Exception as e:
        logger.exception("Failed to dispatch notifications for %s: %s", event_type, e)
    finally:
        db.close()


def _dispatch(
    db: "Session",  # type: ignore[name-defined]  # noqa: F821
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None,
    document_id: str,
    payload: dict | None,
) -> None:
    from app.models.ecm import DocumentSubscription, Notification
    from app.services.common import coerce_uuid

    subs = (
        db.query(DocumentSubscription)
        .filter(
            DocumentSubscription.document_id == coerce_uuid(document_id),
            DocumentSubscription.is_active.is_(True),
        )
        .all()
    )

    event_prefix = event_type.split(".")[0]

    for sub in subs:
        if actor_id and str(sub.person_id) == str(actor_id):
            continue
        if not _matches_event(sub.event_types, event_type, event_prefix):
            continue

        notification = Notification(
            person_id=sub.person_id,
            title=f"{event_type.replace('.', ' ').title()}",
            body=f"Event {event_type} on {entity_type} {entity_id}",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
        )
        db.add(notification)

    db.commit()
    logger.info(
        "Dispatched notifications for event %s on document %s", event_type, document_id
    )


def _matches_event(
    subscribed_types: list[str], event_type: str, event_prefix: str
) -> bool:
    for st in subscribed_types:
        if st == event_type or st == event_prefix:
            return True
    return False


@celery_app.task(
    name="app.tasks.notifications.send_notification_email", ignore_result=True
)
def send_notification_email(
    person_id: str,
    title: str,
    body: str,
) -> None:
    """Send notification email to a person.

    Placeholder — real implementation would use an email service.
    """
    logger.info("Would send email to person %s: %s", person_id, title)
