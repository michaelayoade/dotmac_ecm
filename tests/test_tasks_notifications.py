import uuid

import pytest

from app.models.ecm import DocumentSubscription, Notification


@pytest.fixture()
def subscriber(db_session, person, document):
    """Create a subscriber to a document."""
    sub = DocumentSubscription(
        document_id=document.id,
        person_id=person.id,
        event_types=["document", "comment.created"],
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


@pytest.fixture()
def second_person(db_session):
    from app.models.person import Person

    p = Person(
        first_name="Second",
        last_name="User",
        email=f"second-{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestDispatchNotifications:
    def test_creates_notification_for_subscriber(
        self, db_session, person, document, subscriber
    ) -> None:
        from app.tasks.notifications import _dispatch

        _dispatch(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(document.id),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 1
        assert notifs[0].event_type == "document.created"

    def test_skips_actor(self, db_session, person, document, subscriber) -> None:
        from app.tasks.notifications import _dispatch

        _dispatch(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(document.id),
            actor_id=str(person.id),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 0

    def test_prefix_matching(self, db_session, person, document, subscriber) -> None:
        from app.tasks.notifications import _dispatch

        _dispatch(
            db_session,
            event_type="document.updated",
            entity_type="document",
            entity_id=str(document.id),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 1

    def test_exact_event_matching(
        self, db_session, person, document, subscriber
    ) -> None:
        from app.tasks.notifications import _dispatch

        _dispatch(
            db_session,
            event_type="comment.created",
            entity_type="comment",
            entity_id=str(uuid.uuid4()),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 1

    def test_no_match_for_unsubscribed_event(
        self, db_session, person, document, subscriber
    ) -> None:
        from app.tasks.notifications import _dispatch

        _dispatch(
            db_session,
            event_type="workflow.started",
            entity_type="workflow_instance",
            entity_id=str(uuid.uuid4()),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 0

    def test_multiple_subscribers(
        self, db_session, person, second_person, document
    ) -> None:
        from app.tasks.notifications import _dispatch

        sub1 = DocumentSubscription(
            document_id=document.id,
            person_id=person.id,
            event_types=["document"],
        )
        sub2 = DocumentSubscription(
            document_id=document.id,
            person_id=second_person.id,
            event_types=["document"],
        )
        db_session.add(sub1)
        db_session.add(sub2)
        db_session.commit()

        _dispatch(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(document.id),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        all_notifs = db_session.query(Notification).all()
        person_ids = {str(n.person_id) for n in all_notifs}
        assert str(person.id) in person_ids
        assert str(second_person.id) in person_ids

    def test_no_notification_for_inactive_subscription(
        self, db_session, person, document
    ) -> None:
        from app.tasks.notifications import _dispatch

        sub = DocumentSubscription(
            document_id=document.id,
            person_id=person.id,
            event_types=["document"],
            is_active=False,
        )
        db_session.add(sub)
        db_session.commit()

        _dispatch(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(document.id),
            actor_id=str(uuid.uuid4()),
            document_id=str(document.id),
            payload={},
        )

        notifs = (
            db_session.query(Notification)
            .filter(Notification.person_id == person.id)
            .all()
        )
        assert len(notifs) == 0


class TestMatchesEvent:
    def test_exact_match(self) -> None:
        from app.tasks.notifications import _matches_event

        assert _matches_event(["document.created"], "document.created", "document")

    def test_prefix_match(self) -> None:
        from app.tasks.notifications import _matches_event

        assert _matches_event(["document"], "document.created", "document")

    def test_no_match(self) -> None:
        from app.tasks.notifications import _matches_event

        assert not _matches_event(["comment"], "document.created", "document")
