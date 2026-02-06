import uuid

import pytest
from fastapi import HTTPException

from app.models.ecm import (
    Document,
    DocumentStatus,
    ClassificationLevel,
    Folder,
)
from app.models.person import Person
from app.models.rbac import Role
from app.schemas.ecm_acl import (
    DocumentACLCreate,
    DocumentACLUpdate,
    FolderACLCreate,
    FolderACLUpdate,
)
from app.services.ecm_acl import DocumentACLs, FolderACLs


def _make_person(db_session):
    p = Person(
        first_name="ACL",
        last_name="Tester",
        email=f"acl-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _make_role(db_session):
    r = Role(
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="Test role",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


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


class TestDocumentACLs:
    def test_create_with_person_principal(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        principal = _make_person(db_session)

        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="person",
            principal_id=principal.id,
            permission="read",
            granted_by=person.id,
        )
        acl = DocumentACLs.create(db_session, payload)
        assert acl.document_id == doc.id
        assert acl.principal_id == principal.id
        assert acl.principal_type.value == "person"
        assert acl.permission.value == "read"
        assert acl.is_active is True

    def test_create_with_role_principal(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        role = _make_role(db_session)

        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="role",
            principal_id=role.id,
            permission="write",
            granted_by=person.id,
        )
        acl = DocumentACLs.create(db_session, payload)
        assert acl.principal_type.value == "role"
        assert acl.permission.value == "write"

    def test_create_invalid_document(self, db_session):
        person = _make_person(db_session)
        payload = DocumentACLCreate(
            document_id=uuid.uuid4(),
            principal_type="person",
            principal_id=person.id,
            permission="read",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_principal(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="person",
            principal_id=uuid.uuid4(),
            permission="read",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Person not found" in exc.value.detail

    def test_create_invalid_principal_type(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="invalid",
            principal_id=person.id,
            permission="read",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_create_invalid_permission(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="person",
            principal_id=person.id,
            permission="invalid",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_create_invalid_grantor(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="person",
            principal_id=person.id,
            permission="read",
            granted_by=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Grantor not found" in exc.value.detail

    def test_get(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentACLCreate(
            document_id=doc.id,
            principal_type="person",
            principal_id=person.id,
            permission="read",
            granted_by=person.id,
        )
        acl = DocumentACLs.create(db_session, payload)
        found = DocumentACLs.get(db_session, str(acl.id))
        assert found.id == acl.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_document(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        DocumentACLs.create(
            db_session,
            DocumentACLCreate(
                document_id=doc.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        results = DocumentACLs.list(
            db_session,
            document_id=str(doc.id),
            principal_type=None,
            principal_id=None,
            permission=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.document_id == doc.id for r in results)

    def test_list_filter_by_permission(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        DocumentACLs.create(
            db_session,
            DocumentACLCreate(
                document_id=doc.id,
                principal_type="person",
                principal_id=person.id,
                permission="manage",
                granted_by=person.id,
            ),
        )
        results = DocumentACLs.list(
            db_session,
            document_id=str(doc.id),
            principal_type=None,
            principal_id=None,
            permission="manage",
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.permission.value == "manage" for r in results)

    def test_update(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        acl = DocumentACLs.create(
            db_session,
            DocumentACLCreate(
                document_id=doc.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        updated = DocumentACLs.update(
            db_session,
            str(acl.id),
            DocumentACLUpdate(permission="write"),
        )
        assert updated.permission.value == "write"

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        acl = DocumentACLs.create(
            db_session,
            DocumentACLCreate(
                document_id=doc.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        DocumentACLs.delete(db_session, str(acl.id))
        db_session.refresh(acl)
        assert acl.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentACLs.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestFolderACLs:
    def test_create_with_person_principal(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        principal = _make_person(db_session)

        payload = FolderACLCreate(
            folder_id=folder.id,
            principal_type="person",
            principal_id=principal.id,
            permission="read",
            granted_by=person.id,
        )
        acl = FolderACLs.create(db_session, payload)
        assert acl.folder_id == folder.id
        assert acl.principal_type.value == "person"
        assert acl.is_inherited is False

    def test_create_with_role_principal(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        role = _make_role(db_session)

        payload = FolderACLCreate(
            folder_id=folder.id,
            principal_type="role",
            principal_id=role.id,
            permission="manage",
            granted_by=person.id,
        )
        acl = FolderACLs.create(db_session, payload)
        assert acl.principal_type.value == "role"

    def test_create_with_inherited_flag(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        payload = FolderACLCreate(
            folder_id=folder.id,
            principal_type="person",
            principal_id=person.id,
            permission="read",
            is_inherited=True,
            granted_by=person.id,
        )
        acl = FolderACLs.create(db_session, payload)
        assert acl.is_inherited is True

    def test_create_invalid_folder(self, db_session):
        person = _make_person(db_session)
        payload = FolderACLCreate(
            folder_id=uuid.uuid4(),
            principal_type="person",
            principal_id=person.id,
            permission="read",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            FolderACLs.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Folder not found" in exc.value.detail

    def test_create_invalid_principal(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        payload = FolderACLCreate(
            folder_id=folder.id,
            principal_type="role",
            principal_id=uuid.uuid4(),
            permission="read",
            granted_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            FolderACLs.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Role not found" in exc.value.detail

    def test_get(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        acl = FolderACLs.create(
            db_session,
            FolderACLCreate(
                folder_id=folder.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        found = FolderACLs.get(db_session, str(acl.id))
        assert found.id == acl.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            FolderACLs.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_folder(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        FolderACLs.create(
            db_session,
            FolderACLCreate(
                folder_id=folder.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        results = FolderACLs.list(
            db_session,
            folder_id=str(folder.id),
            principal_type=None,
            principal_id=None,
            permission=None,
            is_inherited=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_list_filter_by_inherited(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        FolderACLs.create(
            db_session,
            FolderACLCreate(
                folder_id=folder.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                is_inherited=True,
                granted_by=person.id,
            ),
        )
        results = FolderACLs.list(
            db_session,
            folder_id=str(folder.id),
            principal_type=None,
            principal_id=None,
            permission=None,
            is_inherited=True,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.is_inherited is True for r in results)

    def test_update(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        acl = FolderACLs.create(
            db_session,
            FolderACLCreate(
                folder_id=folder.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        updated = FolderACLs.update(
            db_session,
            str(acl.id),
            FolderACLUpdate(permission="delete", is_inherited=True),
        )
        assert updated.permission.value == "delete"
        assert updated.is_inherited is True

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        acl = FolderACLs.create(
            db_session,
            FolderACLCreate(
                folder_id=folder.id,
                principal_type="person",
                principal_id=person.id,
                permission="read",
                granted_by=person.id,
            ),
        )
        FolderACLs.delete(db_session, str(acl.id))
        db_session.refresh(acl)
        assert acl.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            FolderACLs.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404
