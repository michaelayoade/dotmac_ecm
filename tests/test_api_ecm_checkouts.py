import uuid

from app.models.ecm import (
    ClassificationLevel,
    Document,
    DocumentStatus,
)
from app.models.person import Person


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="Checkout",
        email=f"api-co-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _create_document(db_session, person):
    doc = Document(
        title="Test Doc",
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


class TestCheckoutEndpoints:
    def test_checkout(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
                "reason": "Editing document",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] == str(doc.id)
        assert data["checked_out_by"] == str(person.id)
        assert data["reason"] == "Editing document"

    def test_get_checkout(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.get(f"/ecm/documents/{doc.id}/checkout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["document_id"] == str(doc.id)

    def test_get_checkout_not_found(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.get(f"/ecm/documents/{doc.id}/checkout", headers=auth_headers)
        assert resp.status_code == 404

    def test_checkin(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.post(
            f"/ecm/documents/{doc.id}/checkin",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "checked in" in resp.json()["detail"]

    def test_force_unlock(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.delete(f"/ecm/documents/{doc.id}/checkout", headers=auth_headers)
        assert resp.status_code == 204

    def test_list_checkouts(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.get("/ecm/documents/checkouts", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_checkout_conflict(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        other = _create_person(db_session)
        client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.post(
            f"/ecm/documents/{doc.id}/checkout",
            json={
                "document_id": str(doc.id),
                "checked_out_by": str(other.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409
