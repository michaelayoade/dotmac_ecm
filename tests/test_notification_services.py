import uuid

import pytest
from fastapi import HTTPException

from app.models.ecm import Notification


@pytest.fixture()
def notification(db_session, person):
    n = Notification(
        person_id=person.id,
        title="Test Notification",
        body="Something happened",
        event_type="document.created",
        entity_type="document",
        entity_id=str(uuid.uuid4()),
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)
    return n


@pytest.fixture()
def notifications_batch(db_session, person):
    items = []
    for i in range(5):
        n = Notification(
            person_id=person.id,
            title=f"Notification {i}",
            body=f"Body {i}",
            event_type="document.updated" if i % 2 == 0 else "comment.created",
            entity_type="document",
            entity_id=str(uuid.uuid4()),
        )
        db_session.add(n)
        items.append(n)
    db_session.commit()
    for n in items:
        db_session.refresh(n)
    return items


class TestNotificationsService:
    def test_get(self, db_session, notification) -> None:
        from app.services.notification import notifications

        result = notifications.get(db_session, str(notification.id))
        assert result.id == notification.id
        assert result.title == "Test Notification"

    def test_get_not_found(self, db_session) -> None:
        from app.services.notification import notifications

        with pytest.raises(HTTPException) as exc:
            notifications.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_all(self, db_session, notifications_batch) -> None:
        from app.services.notification import notifications

        result = notifications.list(
            db_session,
            person_id=str(notifications_batch[0].person_id),
            event_type=None,
            is_read=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) == 5

    def test_list_filter_by_event_type(self, db_session, notifications_batch) -> None:
        from app.services.notification import notifications

        result = notifications.list(
            db_session,
            person_id=str(notifications_batch[0].person_id),
            event_type="comment.created",
            is_read=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) == 2

    def test_list_filter_is_read(self, db_session, notifications_batch) -> None:
        from app.services.notification import notifications

        result = notifications.list(
            db_session,
            person_id=str(notifications_batch[0].person_id),
            event_type=None,
            is_read=False,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) == 5

    def test_mark_read(self, db_session, notifications_batch) -> None:
        from app.services.notification import notifications

        ids = [str(n.id) for n in notifications_batch[:3]]
        count = notifications.mark_read(db_session, ids)
        assert count == 3
        for nid in ids:
            n = db_session.get(Notification, uuid.UUID(nid))
            assert n.is_read is True
            assert n.read_at is not None

    def test_mark_read_idempotent(self, db_session, notifications_batch) -> None:
        from app.services.notification import notifications

        ids = [str(notifications_batch[0].id)]
        notifications.mark_read(db_session, ids)
        count = notifications.mark_read(db_session, ids)
        assert count == 0

    def test_mark_all_read(self, db_session, person, notifications_batch) -> None:
        from app.services.notification import notifications

        count = notifications.mark_all_read(db_session, str(person.id))
        assert count == 5

    def test_mark_all_read_person_not_found(self, db_session) -> None:
        from app.services.notification import notifications

        with pytest.raises(HTTPException) as exc:
            notifications.mark_all_read(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_unread_count(self, db_session, person, notifications_batch) -> None:
        from app.services.notification import notifications

        count = notifications.unread_count(db_session, str(person.id))
        assert count == 5

    def test_unread_count_after_mark_read(
        self, db_session, person, notifications_batch
    ) -> None:
        from app.services.notification import notifications

        notifications.mark_read(db_session, [str(notifications_batch[0].id)])
        count = notifications.unread_count(db_session, str(person.id))
        assert count == 4

    def test_unread_count_person_not_found(self, db_session) -> None:
        from app.services.notification import notifications

        with pytest.raises(HTTPException) as exc:
            notifications.unread_count(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_dismiss(self, db_session, notification) -> None:
        from app.services.notification import notifications

        notifications.dismiss(db_session, str(notification.id))
        n = db_session.get(Notification, notification.id)
        assert n.is_active is False

    def test_dismiss_not_found(self, db_session) -> None:
        from app.services.notification import notifications

        with pytest.raises(HTTPException) as exc:
            notifications.dismiss(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_dismissed_excluded_from_default_list(
        self, db_session, person, notification
    ) -> None:
        from app.services.notification import notifications

        notifications.dismiss(db_session, str(notification.id))
        result = notifications.list(
            db_session,
            person_id=str(person.id),
            event_type=None,
            is_read=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) == 0

    def test_list_includes_dismissed_when_explicitly_requested(
        self, db_session, person, notification
    ) -> None:
        from app.services.notification import notifications

        notifications.dismiss(db_session, str(notification.id))
        result = notifications.list(
            db_session,
            person_id=str(person.id),
            event_type=None,
            is_read=None,
            is_active=False,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) == 1

    def test_mark_all_read_skips_dismissed(
        self, db_session, person, notifications_batch
    ) -> None:
        from app.services.notification import notifications

        notifications.dismiss(db_session, str(notifications_batch[0].id))
        count = notifications.mark_all_read(db_session, str(person.id))
        assert count == 4
