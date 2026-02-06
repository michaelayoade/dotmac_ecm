import uuid

from app.models.ecm import (
    ClassificationLevel,
    Document,
    DocumentStatus,
    Folder,
)
from app.models.person import Person
from app.models.rbac import Role


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="ACL",
        email=f"api-acl-{uuid.uuid4().hex[:8]}@test.com",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _create_role(db_session):
    r = Role(
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="Test role",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


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


class TestDocumentACLEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] == str(doc.id)
        assert data["permission"] == "read"

    def test_create_with_role(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        role = _create_role(db_session)
        resp = client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "role",
                "principal_id": str(role.id),
                "permission": "write",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["principal_type"] == "role"

    def test_get(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        create_resp = client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.get(f"/ecm/document-acls/{acl_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == acl_id

    def test_list(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.get("/ecm/document-acls", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        create_resp = client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.patch(
            f"/ecm/document-acls/{acl_id}",
            json={"permission": "write"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["permission"] == "write"

    def test_delete(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        create_resp = client.post(
            "/ecm/document-acls",
            json={
                "document_id": str(doc.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.delete(f"/ecm/document-acls/{acl_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestFolderACLEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        resp = client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["folder_id"] == str(folder.id)
        assert data["is_inherited"] is False

    def test_create_inherited(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        resp = client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "is_inherited": True,
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_inherited"] is True

    def test_get(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        create_resp = client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.get(f"/ecm/folder-acls/{acl_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_list(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        resp = client.get("/ecm/folder-acls", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        create_resp = client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.patch(
            f"/ecm/folder-acls/{acl_id}",
            json={"permission": "manage"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["permission"] == "manage"

    def test_delete(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        create_resp = client.post(
            "/ecm/folder-acls",
            json={
                "folder_id": str(folder.id),
                "principal_type": "person",
                "principal_id": str(person.id),
                "permission": "read",
                "granted_by": str(person.id),
            },
            headers=auth_headers,
        )
        acl_id = create_resp.json()["id"]
        resp = client.delete(f"/ecm/folder-acls/{acl_id}", headers=auth_headers)
        assert resp.status_code == 204
