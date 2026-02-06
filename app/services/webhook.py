import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import WebhookDelivery, WebhookDeliveryStatus, WebhookEndpoint
from app.models.person import Person
from app.schemas.webhook import WebhookEndpointCreate, WebhookEndpointUpdate
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


class WebhookEndpoints(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: WebhookEndpointCreate) -> WebhookEndpoint:
        if not db.get(Person, coerce_uuid(payload.created_by)):
            raise HTTPException(status_code=404, detail="Creator not found")
        data = payload.model_dump()
        endpoint = WebhookEndpoint(**data)
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        logger.info("Created webhook endpoint %s", endpoint.id)
        return endpoint

    @staticmethod
    def get(db: Session, endpoint_id: str) -> WebhookEndpoint:
        endpoint = db.get(WebhookEndpoint, coerce_uuid(endpoint_id))
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        return endpoint

    @staticmethod
    def list(
        db: Session,
        created_by: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[WebhookEndpoint]:
        query = db.query(WebhookEndpoint)
        if created_by is not None:
            query = query.filter(WebhookEndpoint.created_by == coerce_uuid(created_by))
        if is_active is None:
            query = query.filter(WebhookEndpoint.is_active.is_(True))
        else:
            query = query.filter(WebhookEndpoint.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {
                "name": WebhookEndpoint.name,
                "created_at": WebhookEndpoint.created_at,
            },
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session, endpoint_id: str, payload: WebhookEndpointUpdate
    ) -> WebhookEndpoint:
        endpoint = db.get(WebhookEndpoint, coerce_uuid(endpoint_id))
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(endpoint, key, value)
        db.commit()
        db.refresh(endpoint)
        logger.info("Updated webhook endpoint %s", endpoint.id)
        return endpoint

    @staticmethod
    def delete(db: Session, endpoint_id: str) -> None:
        endpoint = db.get(WebhookEndpoint, coerce_uuid(endpoint_id))
        if not endpoint:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")
        endpoint.is_active = False
        db.commit()
        logger.info("Soft-deleted webhook endpoint %s", endpoint_id)


class WebhookDeliveries(ListResponseMixin):
    @staticmethod
    def get(db: Session, delivery_id: str) -> WebhookDelivery:
        delivery = db.get(WebhookDelivery, coerce_uuid(delivery_id))
        if not delivery:
            raise HTTPException(status_code=404, detail="Webhook delivery not found")
        return delivery

    @staticmethod
    def list(
        db: Session,
        endpoint_id: str | None,
        event_type: str | None,
        status: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[WebhookDelivery]:
        query = db.query(WebhookDelivery)
        if endpoint_id is not None:
            query = query.filter(
                WebhookDelivery.endpoint_id == coerce_uuid(endpoint_id)
            )
        if event_type is not None:
            query = query.filter(WebhookDelivery.event_type == event_type)
        if status is not None:
            query = query.filter(
                WebhookDelivery.status == WebhookDeliveryStatus(status)
            )
        if is_active is None:
            query = query.filter(WebhookDelivery.is_active.is_(True))
        else:
            query = query.filter(WebhookDelivery.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": WebhookDelivery.created_at},
        )
        return apply_pagination(query, limit, offset).all()


webhook_endpoints = WebhookEndpoints()
webhook_deliveries = WebhookDeliveries()
