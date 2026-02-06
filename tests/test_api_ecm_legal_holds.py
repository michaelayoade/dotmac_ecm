import uuid

from app.models.ecm import (
    ClassificationLevel,
    Document,
    DocumentStatus,
    Folder,
    LegalHold,
    LegalHoldDocument,
)
from app.models.person import Person


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="LH",
        email=f"api-lh-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _create_folder(db_session, person):
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


def _create_document(db_session, person):
    folder = _create_folder(db_session, person)
    doc = Document(
        title="Test Doc",
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


def _create_hold(db_session, person):
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


def _create_lhd(db_session, person):
    hold = _create_hold(db_session, person)
    doc = _create_document(db_session, person)
    lhd = LegalHoldDocument(
        legal_hold_id=hold.id,
        document_id=doc.id,
        added_by=person.id,
    )
    db_session.add(lhd)
    db_session.commit()
    db_session.refresh(lhd)
    return lhd


class TestLegalHoldEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        resp = client.post(
            "/ecm/legal-holds",
            json={
                "name": f"hold_{uuid.uuid4().hex[:8]}",
                "description": "Test",
                "reference_number": "REF-001",
                "created_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert "id" in data
        assert data["created_by"] == str(person.id)

    def test_create_invalid_creator(self, client, auth_headers):
        resp = client.post(
            "/ecm/legal-holds",
            json={
                "name": f"hold_{uuid.uuid4().hex[:8]}",
                "created_by": str(uuid.uuid4()),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        resp = client.get(
            f"/ecm/legal-holds/{hold.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(hold.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/legal-holds/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session, person):
        _create_hold(db_session, person)
        resp = client.get("/ecm/legal-holds", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 1

    def test_update(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        resp = client.patch(
            f"/ecm/legal-holds/{hold.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    def test_delete(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        resp = client.delete(
            f"/ecm/legal-holds/{hold.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestLegalHoldDocumentEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/legal-hold-documents",
            json={
                "legal_hold_id": str(hold.id),
                "document_id": str(doc.id),
                "added_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["legal_hold_id"] == str(hold.id)
        assert data["document_id"] == str(doc.id)

    def test_create_invalid_hold(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/legal-hold-documents",
            json={
                "legal_hold_id": str(uuid.uuid4()),
                "document_id": str(doc.id),
                "added_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_create_invalid_document(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        resp = client.post(
            "/ecm/legal-hold-documents",
            json={
                "legal_hold_id": str(hold.id),
                "document_id": str(uuid.uuid4()),
                "added_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        lhd = _create_lhd(db_session, person)
        resp = client.get(
            f"/ecm/legal-hold-documents/{lhd.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(lhd.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/legal-hold-documents/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session, person):
        _create_lhd(db_session, person)
        resp = client.get("/ecm/legal-hold-documents", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_filter_hold(self, client, auth_headers, db_session, person):
        hold = _create_hold(db_session, person)
        doc = _create_document(db_session, person)
        lhd = LegalHoldDocument(
            legal_hold_id=hold.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd)
        db_session.commit()
        resp = client.get(
            f"/ecm/legal-hold-documents?legal_hold_id={hold.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_delete(self, client, auth_headers, db_session, person):
        lhd = _create_lhd(db_session, person)
        resp = client.delete(
            f"/ecm/legal-hold-documents/{lhd.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete(
            f"/ecm/legal-hold-documents/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
