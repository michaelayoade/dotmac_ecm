import uuid

from app.models.ecm import (
    Document,
    DocumentStatus,
    ClassificationLevel,
    DocumentVersion,
)


def _create_document(db_session, person, **overrides):
    defaults = dict(
        title="Test Doc",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
        status=DocumentStatus.draft,
        classification=ClassificationLevel.internal,
    )
    defaults.update(overrides)
    doc = Document(**defaults)
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _create_version(db_session, doc, person, version_number=2):
    version = DocumentVersion(
        document_id=doc.id,
        version_number=version_number,
        file_name=f"v{version_number}.pdf",
        file_size=2048,
        mime_type="application/pdf",
        storage_key=f"documents/{doc.id}/v{version_number}.pdf",
        checksum_sha256="a" * 64,
        created_by=person.id,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version


class TestDocumentEndpoints:
    def test_create_document(self, client, auth_headers, person):
        resp = client.post(
            "/ecm/documents",
            json={
                "title": "New Document",
                "file_name": "new.pdf",
                "file_size": 2048,
                "mime_type": "application/pdf",
                "created_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Document"

    def test_get_document(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.get(f"/ecm/documents/{doc.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(doc.id)

    def test_get_document_not_found(self, client, auth_headers):
        resp = client.get(f"/ecm/documents/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_documents(self, client, auth_headers, db_session, person):
        _create_document(db_session, person, title=f"D_{uuid.uuid4().hex[:6]}")
        resp = client.get("/ecm/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update_document(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.patch(
            f"/ecm/documents/{doc.id}",
            json={"title": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_delete_document(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.delete(f"/ecm/documents/{doc.id}", headers=auth_headers)
        assert resp.status_code == 204


class TestVersionEndpoints:
    def test_create_version(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            f"/ecm/documents/{doc.id}/versions",
            json={
                "document_id": str(doc.id),
                "file_name": "v2.pdf",
                "file_size": 3000,
                "mime_type": "application/pdf",
                "storage_key": "documents/test/v2.pdf",
                "checksum_sha256": "b" * 64,
                "created_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["version_number"] == 2

    def test_get_version(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        version = _create_version(db_session, doc, person)
        resp = client.get(
            f"/ecm/documents/{doc.id}/versions/{version.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_versions(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        _create_version(db_session, doc, person)
        resp = client.get(f"/ecm/documents/{doc.id}/versions", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_delete_version(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        v1 = _create_version(db_session, doc, person, version_number=2)
        # Create v3 so v2 is not current
        _create_version(db_session, doc, person, version_number=3)
        doc.current_version_id = None  # ensure v2 is NOT current
        db_session.commit()
        resp = client.delete(
            f"/ecm/documents/{doc.id}/versions/{v1.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204
