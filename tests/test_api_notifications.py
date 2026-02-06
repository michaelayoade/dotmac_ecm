import uuid

import pytest

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
    for i in range(3):
        n = Notification(
            person_id=person.id,
            title=f"Notification {i}",
            body=f"Body {i}",
            event_type="document.updated",
            entity_type="document",
            entity_id=str(uuid.uuid4()),
        )
        db_session.add(n)
        items.append(n)
    db_session.commit()
    for n in items:
        db_session.refresh(n)
    return items


class TestNotificationEndpoints:
    def test_get(self, client, auth_headers, notification) -> None:
        resp = client.get(f"/notifications/{notification.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(notification.id)

    def test_get_not_found(self, client, auth_headers) -> None:
        resp = client.get(f"/notifications/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, person, notifications_batch) -> None:
        resp = client.get(f"/notifications?person_id={person.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3

    def test_list_filter_is_read(
        self, client, auth_headers, person, notifications_batch
    ) -> None:
        resp = client.get(
            f"/notifications?person_id={person.id}&is_read=false",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_mark_read(self, client, auth_headers, notifications_batch) -> None:
        ids = [str(n.id) for n in notifications_batch[:2]]
        resp = client.post(
            "/notifications/mark-read",
            json={"notification_ids": ids},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["marked"] == 2

    def test_mark_all_read(
        self, client, auth_headers, person, notifications_batch
    ) -> None:
        resp = client.post(
            "/notifications/mark-all-read",
            json={"person_id": str(person.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["marked"] == 3

    def test_unread_count(
        self, client, auth_headers, person, notifications_batch
    ) -> None:
        resp = client.get(
            f"/notifications/unread-count?person_id={person.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_dismiss(self, client, auth_headers, notification) -> None:
        resp = client.delete(f"/notifications/{notification.id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_dismiss_not_found(self, client, auth_headers) -> None:
        resp = client.delete(f"/notifications/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_pagination(
        self, client, auth_headers, person, notifications_batch
    ) -> None:
        resp = client.get(
            f"/notifications?person_id={person.id}&limit=2&offset=0",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_v1_prefix(self, client, auth_headers, notification) -> None:
        resp = client.get(
            f"/api/v1/notifications/{notification.id}", headers=auth_headers
        )
        assert resp.status_code == 200
