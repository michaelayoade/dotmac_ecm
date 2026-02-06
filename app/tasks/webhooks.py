import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.webhooks.deliver_webhooks", ignore_result=True)
def deliver_webhooks(
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    document_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """Find matching webhook endpoints and queue individual deliveries."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        _find_and_queue(
            db, event_type, entity_type, entity_id, actor_id, document_id, payload
        )
    except Exception as e:
        logger.exception("Failed to deliver webhooks for %s: %s", event_type, e)
    finally:
        db.close()


def _find_and_queue(
    db: "Session",  # type: ignore[name-defined]  # noqa: F821
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None,
    document_id: str | None,
    payload: dict | None,
) -> None:
    from app.models.ecm import WebhookDeliveryStatus, WebhookEndpoint, WebhookDelivery

    endpoints = (
        db.query(WebhookEndpoint).filter(WebhookEndpoint.is_active.is_(True)).all()
    )

    event_prefix = event_type.split(".")[0]
    event_data = {
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_id": actor_id,
        "document_id": document_id,
        "payload": payload or {},
    }

    for ep in endpoints:
        if not _endpoint_matches(ep.event_types, event_type, event_prefix):
            continue

        delivery = WebhookDelivery(
            endpoint_id=ep.id,
            event_type=event_type,
            payload=event_data,
            status=WebhookDeliveryStatus.pending,
        )
        db.add(delivery)
        db.flush()

        deliver_single_webhook.delay(
            delivery_id=str(delivery.id),
            url=ep.url,
            secret=ep.secret,
            payload=event_data,
        )

    db.commit()
    logger.info("Queued webhook deliveries for event %s", event_type)


def _endpoint_matches(
    subscribed_types: list[str], event_type: str, event_prefix: str
) -> bool:
    if not subscribed_types:
        return True
    for st in subscribed_types:
        if st == event_type or st == event_prefix:
            return True
    return False


@celery_app.task(
    name="app.tasks.webhooks.deliver_single_webhook",
    ignore_result=True,
    bind=True,
    max_retries=5,
    default_retry_delay=10,
)
def deliver_single_webhook(
    self: "celery_app.Task",  # type: ignore[name-defined]
    delivery_id: str,
    url: str,
    secret: str | None,
    payload: dict,
) -> None:
    """Deliver a single webhook via HTTP POST with HMAC signing."""
    import httpx

    from app.db import SessionLocal
    from app.models.ecm import WebhookDelivery, WebhookDeliveryStatus
    from app.services.common import coerce_uuid

    body = json.dumps(payload, default=str)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = sig

    db = SessionLocal()
    try:
        delivery = db.get(WebhookDelivery, coerce_uuid(delivery_id))
        if not delivery:
            logger.error("WebhookDelivery %s not found", delivery_id)
            return

        delivery.attempts += 1
        delivery.last_attempt_at = datetime.now(timezone.utc)

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, content=body, headers=headers)
            delivery.response_status_code = resp.status_code
            delivery.response_body = resp.text[:4000]
            if 200 <= resp.status_code < 300:
                delivery.status = WebhookDeliveryStatus.success
            else:
                delivery.status = WebhookDeliveryStatus.failed
        except (httpx.HTTPError, OSError) as e:
            logger.warning("Webhook delivery %s failed: %s", delivery_id, e)
            delivery.status = WebhookDeliveryStatus.failed
            delivery.response_body = str(e)[:4000]

        db.commit()

        if delivery.status == WebhookDeliveryStatus.failed:
            try:
                self.retry(countdown=10 * (2 ** (self.request.retries or 0)))
            except self.MaxRetriesExceededError:
                logger.error("Webhook delivery %s exhausted retries", delivery_id)
    finally:
        db.close()
