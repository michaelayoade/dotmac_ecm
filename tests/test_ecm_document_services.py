import uuid

import pytest
from fastapi import HTTPException

from app.schemas.ecm import (
    DocumentCreate,
    DocumentUpdate,
    DocumentVersionCreate,
    FolderCreate,
)
from app.services.ecm_document import Documents
from app.services.ecm_folder import Folders


def _make_doc_payload(person_id, **overrides):
    defaults = dict(
        title="Test Doc",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person_id,
    )
    defaults.update(overrides)
    return DocumentCreate(**defaults)


class TestDocumentsCreate:
    def test_create_document(self, db_session, person):
        payload = _make_doc_payload(person.id)
        doc = Documents.create(db_session, payload)
        assert doc.title == "Test Doc"
        assert doc.status.value == "draft"
        assert doc.classification.value == "internal"
        assert doc.is_active is True

    def test_create_document_with_folder(self, db_session, person):
        folder = Folders.create(
            db_session, FolderCreate(name="docs", created_by=person.id)
        )
        payload = _make_doc_payload(person.id, folder_id=folder.id)
        doc = Documents.create(db_session, payload)
        assert doc.folder_id == folder.id

    def test_create_document_invalid_creator(self, db_session):
        payload = _make_doc_payload(uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            Documents.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Creator" in exc.value.detail

    def test_create_document_invalid_folder(self, db_session, person):
        payload = _make_doc_payload(person.id, folder_id=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            Documents.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Folder" in exc.value.detail

    def test_create_document_invalid_classification(self, db_session, person):
        payload = _make_doc_payload(person.id, classification="top_secret")
        with pytest.raises(HTTPException) as exc:
            Documents.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_create_document_invalid_status(self, db_session, person):
        payload = _make_doc_payload(person.id, status="invalid")
        with pytest.raises(HTTPException) as exc:
            Documents.create(db_session, payload)
        assert exc.value.status_code == 400


class TestDocumentsGet:
    def test_get_document(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        found = Documents.get(db_session, str(doc.id))
        assert found.id == doc.id

    def test_get_document_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Documents.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestDocumentsList:
    def test_list_documents(self, db_session, person):
        Documents.create(db_session, _make_doc_payload(person.id, title="Doc A"))
        Documents.create(db_session, _make_doc_payload(person.id, title="Doc B"))
        results = Documents.list(
            db_session,
            folder_id=None,
            status=None,
            classification=None,
            content_type_id=None,
            created_by=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 2

    def test_list_documents_filter_status(self, db_session, person):
        Documents.create(
            db_session, _make_doc_payload(person.id, title="Active", status="active")
        )
        results = Documents.list(
            db_session,
            folder_id=None,
            status="active",
            classification=None,
            content_type_id=None,
            created_by=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert all(r.status.value == "active" for r in results)


class TestDocumentsUpdate:
    def test_update_document(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        updated = Documents.update(
            db_session, str(doc.id), DocumentUpdate(title="Updated Title")
        )
        assert updated.title == "Updated Title"

    def test_update_document_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Documents.update(db_session, str(uuid.uuid4()), DocumentUpdate(title="X"))
        assert exc.value.status_code == 404


class TestDocumentsDelete:
    def test_soft_delete_document(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        Documents.delete(db_session, str(doc.id))
        db_session.refresh(doc)
        assert doc.is_active is False


class TestDocumentVersions:
    def _create_version_payload(self, doc_id, person_id):
        return DocumentVersionCreate(
            document_id=doc_id,
            file_name="v2.pdf",
            file_size=2048,
            mime_type="application/pdf",
            storage_key="documents/test/v2.pdf",
            checksum_sha256="abc123def456" * 4 + "abcd",
            change_summary="Updated content",
            created_by=person_id,
        )

    def test_create_version(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        payload = self._create_version_payload(doc.id, person.id)
        version = Documents.create_version(db_session, str(doc.id), payload)
        assert version.version_number == 2
        db_session.refresh(doc)
        assert doc.current_version_id == version.id
        assert doc.version_number == 2
        assert doc.file_name == "v2.pdf"

    def test_get_version(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        payload = self._create_version_payload(doc.id, person.id)
        version = Documents.create_version(db_session, str(doc.id), payload)
        found = Documents.get_version(db_session, str(doc.id), str(version.id))
        assert found.id == version.id

    def test_get_version_wrong_document(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        payload = self._create_version_payload(doc.id, person.id)
        version = Documents.create_version(db_session, str(doc.id), payload)
        with pytest.raises(HTTPException) as exc:
            Documents.get_version(db_session, str(uuid.uuid4()), str(version.id))
        assert exc.value.status_code == 404

    def test_list_versions(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        Documents.create_version(
            db_session,
            str(doc.id),
            self._create_version_payload(doc.id, person.id),
        )
        versions = Documents.list_versions(db_session, str(doc.id), 50, 0)
        assert len(versions) >= 1

    def test_delete_version_blocked_for_current(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        payload = self._create_version_payload(doc.id, person.id)
        version = Documents.create_version(db_session, str(doc.id), payload)
        with pytest.raises(HTTPException) as exc:
            Documents.delete_version(db_session, str(doc.id), str(version.id))
        assert exc.value.status_code == 400
        assert "current version" in exc.value.detail

    def test_delete_old_version(self, db_session, person):
        doc = Documents.create(db_session, _make_doc_payload(person.id))
        v1 = Documents.create_version(
            db_session,
            str(doc.id),
            self._create_version_payload(doc.id, person.id),
        )
        # Create v3 so v2 (v1 in our test) is no longer current
        Documents.create_version(
            db_session,
            str(doc.id),
            self._create_version_payload(doc.id, person.id),
        )
        Documents.delete_version(db_session, str(doc.id), str(v1.id))
        db_session.refresh(v1)
        assert v1.is_active is False
