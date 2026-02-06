import uuid

import pytest
from fastapi import HTTPException

from app.models.ecm import (
    Document,
    DocumentStatus,
    ClassificationLevel,
)
from app.models.person import Person
from app.services.ecm_checkout import Checkouts


def _make_person(db_session):
    p = Person(
        first_name="Checkout",
        last_name="Tester",
        email=f"checkout-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _make_document(db_session, person):
    doc = Document(
        title=f"doc_{uuid.uuid4().hex[:8]}",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
        status=DocumentStatus.draft,
        classification=ClassificationLevel.internal,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


class TestCheckout:
    def test_checkout_happy_path(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        co = Checkouts.checkout(db_session, str(doc.id), str(person.id), "Editing")
        assert co.document_id == doc.id
        assert co.checked_out_by == person.id
        assert co.reason == "Editing"
        assert co.checked_out_at is not None

    def test_checkout_without_reason(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        co = Checkouts.checkout(db_session, str(doc.id), str(person.id))
        assert co.reason is None

    def test_checkout_already_checked_out(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        Checkouts.checkout(db_session, str(doc.id), str(person.id))

        person2 = _make_person(db_session)
        with pytest.raises(HTTPException) as exc:
            Checkouts.checkout(db_session, str(doc.id), str(person2.id))
        assert exc.value.status_code == 409
        assert "already checked out" in exc.value.detail

    def test_checkout_invalid_document(self, db_session):
        person = _make_person(db_session)
        with pytest.raises(HTTPException) as exc:
            Checkouts.checkout(db_session, str(uuid.uuid4()), str(person.id))
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_checkout_invalid_person(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        with pytest.raises(HTTPException) as exc:
            Checkouts.checkout(db_session, str(doc.id), str(uuid.uuid4()))
        assert exc.value.status_code == 404
        assert "Person not found" in exc.value.detail


class TestGetCheckout:
    def test_get_checkout(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        original = Checkouts.checkout(db_session, str(doc.id), str(person.id))
        found = Checkouts.get_checkout(db_session, str(doc.id))
        assert found.id == original.id

    def test_get_checkout_not_found(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        with pytest.raises(HTTPException) as exc:
            Checkouts.get_checkout(db_session, str(doc.id))
        assert exc.value.status_code == 404
        assert "not checked out" in exc.value.detail


class TestCheckin:
    def test_checkin_happy_path(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        Checkouts.checkout(db_session, str(doc.id), str(person.id))
        Checkouts.checkin(db_session, str(doc.id), str(person.id))
        # Verify checkout is gone
        with pytest.raises(HTTPException) as exc:
            Checkouts.get_checkout(db_session, str(doc.id))
        assert exc.value.status_code == 404

    def test_checkin_wrong_person(self, db_session):
        person = _make_person(db_session)
        other = _make_person(db_session)
        doc = _make_document(db_session, person)
        Checkouts.checkout(db_session, str(doc.id), str(person.id))
        with pytest.raises(HTTPException) as exc:
            Checkouts.checkin(db_session, str(doc.id), str(other.id))
        assert exc.value.status_code == 403
        assert "another person" in exc.value.detail

    def test_checkin_not_checked_out(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        with pytest.raises(HTTPException) as exc:
            Checkouts.checkin(db_session, str(doc.id), str(person.id))
        assert exc.value.status_code == 404


class TestForceUnlock:
    def test_force_unlock(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        Checkouts.checkout(db_session, str(doc.id), str(person.id))
        Checkouts.force_unlock(db_session, str(doc.id))
        with pytest.raises(HTTPException) as exc:
            Checkouts.get_checkout(db_session, str(doc.id))
        assert exc.value.status_code == 404

    def test_force_unlock_not_checked_out(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        with pytest.raises(HTTPException) as exc:
            Checkouts.force_unlock(db_session, str(doc.id))
        assert exc.value.status_code == 404


class TestListCheckouts:
    def test_list_checkouts(self, db_session):
        person = _make_person(db_session)
        doc1 = _make_document(db_session, person)
        doc2 = _make_document(db_session, person)
        Checkouts.checkout(db_session, str(doc1.id), str(person.id))
        Checkouts.checkout(db_session, str(doc2.id), str(person.id))
        results = Checkouts.list_checkouts(db_session, limit=50, offset=0)
        doc_ids = {r.document_id for r in results}
        assert doc1.id in doc_ids
        assert doc2.id in doc_ids

    def test_list_checkouts_pagination(self, db_session):
        person = _make_person(db_session)
        for _ in range(3):
            doc = _make_document(db_session, person)
            Checkouts.checkout(db_session, str(doc.id), str(person.id))
        results = Checkouts.list_checkouts(db_session, limit=1, offset=0)
        assert len(results) == 1
