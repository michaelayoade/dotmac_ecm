import uuid

import pytest
from fastapi import HTTPException

from app.models.ecm import (
    ClassificationLevel,
    Document,
    DocumentStatus,
    Folder,
    LegalHold,
    LegalHoldDocument,
)
from app.models.person import Person
from app.schemas.ecm_legal_hold import (
    LegalHoldCreate,
    LegalHoldDocumentCreate,
    LegalHoldUpdate,
)
from app.services.ecm_legal_hold import (
    LegalHoldDocuments,
    LegalHolds,
)


def _make_person(db_session):
    p = Person(
        first_name="LH",
        last_name="Tester",
        email=f"lh-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _make_folder(db_session, person):
    f = Folder(
        name=f"folder_{uuid.uuid4().hex[:8]}",
        created_by=person.id,
        path=f"/folder_{uuid.uuid4().hex[:8]}",
        depth=0,
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)
    return f


def _make_document(db_session, person):
    folder = _make_folder(db_session, person)
    doc = Document(
        title=f"doc_{uuid.uuid4().hex[:8]}",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
        folder_id=folder.id,
        status=DocumentStatus.draft,
        classification=ClassificationLevel.internal,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _make_hold(db_session, person):
    hold = LegalHold(
        name=f"hold_{uuid.uuid4().hex[:8]}",
        description="Test legal hold",
        reference_number=f"REF-{uuid.uuid4().hex[:6]}",
        created_by=person.id,
    )
    db_session.add(hold)
    db_session.commit()
    db_session.refresh(hold)
    return hold


def _make_lhd(db_session, person, hold=None, doc=None):
    if hold is None:
        hold = _make_hold(db_session, person)
    if doc is None:
        doc = _make_document(db_session, person)
    lhd = LegalHoldDocument(
        legal_hold_id=hold.id,
        document_id=doc.id,
        added_by=person.id,
    )
    db_session.add(lhd)
    db_session.commit()
    db_session.refresh(lhd)
    return lhd


class TestLegalHolds:
    def test_create(self, db_session):
        person = _make_person(db_session)
        payload = LegalHoldCreate(
            name=f"hold_{uuid.uuid4().hex[:8]}",
            description="Test hold",
            reference_number="REF-001",
            created_by=person.id,
        )
        hold = LegalHolds.create(db_session, payload)
        assert hold.name == payload.name
        assert hold.created_by == person.id
        assert hold.is_active is True

    def test_create_invalid_creator(self, db_session):
        payload = LegalHoldCreate(
            name=f"hold_{uuid.uuid4().hex[:8]}",
            created_by=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            LegalHolds.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Creator not found" in exc.value.detail

    def test_get(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        found = LegalHolds.get(db_session, str(hold.id))
        assert found.id == hold.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            LegalHolds.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_default_active(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        results = LegalHolds.list(
            db_session,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert hold.id in ids

    def test_list_filter_inactive(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        hold.is_active = False
        db_session.commit()
        results = LegalHolds.list(
            db_session,
            is_active=False,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert hold.id in ids

    def test_list_order_by_name(self, db_session):
        person = _make_person(db_session)
        _make_hold(db_session, person)
        results = LegalHolds.list(
            db_session,
            is_active=None,
            order_by="name",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        updated = LegalHolds.update(
            db_session,
            str(hold.id),
            LegalHoldUpdate(description="Updated description"),
        )
        assert updated.description == "Updated description"

    def test_update_name(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        new_name = f"updated_{uuid.uuid4().hex[:8]}"
        updated = LegalHolds.update(
            db_session,
            str(hold.id),
            LegalHoldUpdate(name=new_name),
        )
        assert updated.name == new_name

    def test_update_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            LegalHolds.update(
                db_session,
                str(uuid.uuid4()),
                LegalHoldUpdate(description="x"),
            )
        assert exc.value.status_code == 404

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        LegalHolds.delete(db_session, str(hold.id))
        db_session.refresh(hold)
        assert hold.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            LegalHolds.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestLegalHoldDocuments:
    def test_create(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        doc = _make_document(db_session, person)
        payload = LegalHoldDocumentCreate(
            legal_hold_id=hold.id,
            document_id=doc.id,
            added_by=person.id,
        )
        lhd = LegalHoldDocuments.create(db_session, payload)
        assert lhd.legal_hold_id == hold.id
        assert lhd.document_id == doc.id
        assert lhd.added_by == person.id

    def test_create_invalid_hold(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = LegalHoldDocumentCreate(
            legal_hold_id=uuid.uuid4(),
            document_id=doc.id,
            added_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            LegalHoldDocuments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Legal hold not found" in exc.value.detail

    def test_create_invalid_document(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        payload = LegalHoldDocumentCreate(
            legal_hold_id=hold.id,
            document_id=uuid.uuid4(),
            added_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            LegalHoldDocuments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_adder(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        doc = _make_document(db_session, person)
        payload = LegalHoldDocumentCreate(
            legal_hold_id=hold.id,
            document_id=doc.id,
            added_by=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            LegalHoldDocuments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Adder not found" in exc.value.detail

    def test_get(self, db_session):
        person = _make_person(db_session)
        lhd = _make_lhd(db_session, person)
        found = LegalHoldDocuments.get(db_session, str(lhd.id))
        assert found.id == lhd.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            LegalHoldDocuments.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_hold(self, db_session):
        person = _make_person(db_session)
        hold = _make_hold(db_session, person)
        lhd = _make_lhd(db_session, person, hold=hold)
        results = LegalHoldDocuments.list(
            db_session,
            legal_hold_id=str(hold.id),
            document_id=None,
            added_by=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert lhd.id in ids

    def test_list_filter_by_document(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        lhd = _make_lhd(db_session, person, doc=doc)
        results = LegalHoldDocuments.list(
            db_session,
            legal_hold_id=None,
            document_id=str(doc.id),
            added_by=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert lhd.id in ids

    def test_list_filter_by_adder(self, db_session):
        person = _make_person(db_session)
        _make_lhd(db_session, person)
        results = LegalHoldDocuments.list(
            db_session,
            legal_hold_id=None,
            document_id=None,
            added_by=str(person.id),
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.added_by == person.id for r in results)

    def test_hard_delete(self, db_session):
        person = _make_person(db_session)
        lhd = _make_lhd(db_session, person)
        lhd_id = lhd.id
        LegalHoldDocuments.delete(db_session, str(lhd_id))
        assert db_session.get(LegalHoldDocument, lhd_id) is None

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            LegalHoldDocuments.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404
