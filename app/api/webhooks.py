from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.webhook import (
    WebhookDeliveryRead,
    WebhookEndpointCreate,
    WebhookEndpointRead,
    WebhookEndpointUpdate,
)
from app.services.webhook import webhook_deliveries, webhook_endpoints

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/endpoints",
    response_model=WebhookEndpointRead,
    status_code=status.HTTP_201_CREATED,
)
def create_endpoint(payload: WebhookEndpointCreate, db: Session = Depends(get_db)):
    return webhook_endpoints.create(db, payload)


@router.get("/endpoints/{endpoint_id}", response_model=WebhookEndpointRead)
def get_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    return webhook_endpoints.get(db, endpoint_id)


@router.get("/endpoints", response_model=ListResponse[WebhookEndpointRead])
def list_endpoints(
    created_by: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return webhook_endpoints.list_response(
        db,
        created_by,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch("/endpoints/{endpoint_id}", response_model=WebhookEndpointRead)
def update_endpoint(
    endpoint_id: str,
    payload: WebhookEndpointUpdate,
    db: Session = Depends(get_db),
):
    return webhook_endpoints.update(db, endpoint_id, payload)


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    webhook_endpoints.delete(db, endpoint_id)


@router.get("/deliveries", response_model=ListResponse[WebhookDeliveryRead])
def list_deliveries(
    endpoint_id: str | None = None,
    event_type: str | None = None,
    delivery_status: str | None = Query(default=None, alias="status"),
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return webhook_deliveries.list_response(
        db,
        endpoint_id,
        event_type,
        delivery_status,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.get("/deliveries/{delivery_id}", response_model=WebhookDeliveryRead)
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    return webhook_deliveries.get(db, delivery_id)
