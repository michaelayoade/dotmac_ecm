from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.notification import (
    MarkAllReadRequest,
    MarkReadRequest,
    NotificationRead,
    UnreadCountResponse,
)
from app.services.notification import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(person_id: str = Query(...), db: Session = Depends(get_db)):
    count = notifications.unread_count(db, person_id)
    return {"count": count}


@router.get("", response_model=ListResponse[NotificationRead])
def list_notifications(
    person_id: str | None = None,
    event_type: str | None = None,
    is_read: bool | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return notifications.list_response(
        db,
        person_id,
        event_type,
        is_read,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.post("/mark-read")
def mark_read(payload: MarkReadRequest, db: Session = Depends(get_db)):
    count = notifications.mark_read(db, [str(nid) for nid in payload.notification_ids])
    return {"marked": count}


@router.post("/mark-all-read")
def mark_all_read(payload: MarkAllReadRequest, db: Session = Depends(get_db)):
    count = notifications.mark_all_read(db, str(payload.person_id))
    return {"marked": count}


@router.get("/{notification_id}", response_model=NotificationRead)
def get_notification(notification_id: str, db: Session = Depends(get_db)):
    return notifications.get(db, notification_id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_notification(notification_id: str, db: Session = Depends(get_db)):
    notifications.dismiss(db, notification_id)
