from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import Notification
from app.models.person import Person
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


class Notifications(ListResponseMixin):
    @staticmethod
    def get(db: Session, notification_id: str) -> Notification:
        notification = db.get(Notification, coerce_uuid(notification_id))
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        return notification

    @staticmethod
    def list(
        db: Session,
        person_id: str | None,
        event_type: str | None,
        is_read: bool | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> List[Notification]:
        query = db.query(Notification)
        if person_id is not None:
            query = query.filter(Notification.person_id == coerce_uuid(person_id))
        if event_type is not None:
            query = query.filter(Notification.event_type == event_type)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if is_active is None:
            query = query.filter(Notification.is_active.is_(True))
        else:
            query = query.filter(Notification.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": Notification.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def mark_read(db: Session, notification_ids: List[str]) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for nid in notification_ids:
            notification = db.get(Notification, coerce_uuid(nid))
            if notification and not notification.is_read:
                notification.is_read = True
                notification.read_at = now
                count += 1
        db.commit()
        logger.info("Marked %d notifications as read", count)
        return count

    @staticmethod
    def mark_all_read(db: Session, person_id: str) -> int:
        if not db.get(Person, coerce_uuid(person_id)):
            raise HTTPException(status_code=404, detail="Person not found")
        now = datetime.now(timezone.utc)
        notifications = (
            db.query(Notification)
            .filter(
                Notification.person_id == coerce_uuid(person_id),
                Notification.is_read.is_(False),
                Notification.is_active.is_(True),
            )
            .all()
        )
        for n in notifications:
            n.is_read = True
            n.read_at = now
        db.commit()
        logger.info(
            "Marked all %d notifications as read for person %s",
            len(notifications),
            person_id,
        )
        return len(notifications)

    @staticmethod
    def unread_count(db: Session, person_id: str) -> int:
        if not db.get(Person, coerce_uuid(person_id)):
            raise HTTPException(status_code=404, detail="Person not found")
        return (
            db.query(Notification)
            .filter(
                Notification.person_id == coerce_uuid(person_id),
                Notification.is_read.is_(False),
                Notification.is_active.is_(True),
            )
            .count()
        )

    @staticmethod
    def dismiss(db: Session, notification_id: str) -> None:
        notification = db.get(Notification, coerce_uuid(notification_id))
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        notification.is_active = False
        db.commit()
        logger.info("Dismissed notification %s", notification_id)


notifications = Notifications()
