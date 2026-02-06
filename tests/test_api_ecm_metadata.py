import uuid

from app.models.ecm import (
    Category,
    ContentType,
    Document,
    DocumentStatus,
    ClassificationLevel,
    Tag,
)


def _create_content_type(db_session, name=None):
    ct = ContentType(name=name or f"CT_{uuid.uuid4().hex[:6]}")
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return ct


def _create_tag(db_session, name=None):
    tag = Tag(name=name or f"tag_{uuid.uuid4().hex[:6]}")
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


def _create_category(db_session, name=None, parent_id=None):
    cat = Category(
        name=name or f"cat_{uuid.uuid4().hex[:6]}",
        parent_id=parent_id,
        path=f"/{name or 'cat'}",
        depth=0,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


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


class TestContentTypeEndpoints:
    def test_create(self, client, auth_headers):
        resp = client.post(
            "/ecm/content-types",
            json={"name": f"CT_{uuid.uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_get(self, client, auth_headers, db_session):
        ct = _create_content_type(db_session)
        resp = client.get(f"/ecm/content-types/{ct.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_list(self, client, auth_headers, db_session):
        _create_content_type(db_session)
        resp = client.get("/ecm/content-types", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update(self, client, auth_headers, db_session):
        ct = _create_content_type(db_session)
        resp = client.patch(
            f"/ecm/content-types/{ct.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete(self, client, auth_headers, db_session):
        ct = _create_content_type(db_session)
        resp = client.delete(f"/ecm/content-types/{ct.id}", headers=auth_headers)
        assert resp.status_code == 204


class TestTagEndpoints:
    def test_create(self, client, auth_headers):
        resp = client.post(
            "/ecm/tags",
            json={"name": f"tag_{uuid.uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_get(self, client, auth_headers, db_session):
        tag = _create_tag(db_session)
        resp = client.get(f"/ecm/tags/{tag.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_list(self, client, auth_headers, db_session):
        _create_tag(db_session)
        resp = client.get("/ecm/tags", headers=auth_headers)
        assert resp.status_code == 200

    def test_update(self, client, auth_headers, db_session):
        tag = _create_tag(db_session)
        resp = client.patch(
            f"/ecm/tags/{tag.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete(self, client, auth_headers, db_session):
        tag = _create_tag(db_session)
        resp = client.delete(f"/ecm/tags/{tag.id}", headers=auth_headers)
        assert resp.status_code == 204


class TestDocumentTagEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        tag = _create_tag(db_session)
        resp = client.post(
            "/ecm/document-tags",
            json={"document_id": str(doc.id), "tag_id": str(tag.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_list(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        tag = _create_tag(db_session)
        client.post(
            "/ecm/document-tags",
            json={"document_id": str(doc.id), "tag_id": str(tag.id)},
            headers=auth_headers,
        )
        resp = client.get("/ecm/document-tags", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        tag = _create_tag(db_session)
        create_resp = client.post(
            "/ecm/document-tags",
            json={"document_id": str(doc.id), "tag_id": str(tag.id)},
            headers=auth_headers,
        )
        link_id = create_resp.json()["id"]
        resp = client.delete(f"/ecm/document-tags/{link_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestCategoryEndpoints:
    def test_create(self, client, auth_headers):
        resp = client.post(
            "/ecm/categories",
            json={"name": f"cat_{uuid.uuid4().hex[:6]}"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_get(self, client, auth_headers, db_session):
        cat = _create_category(db_session, name="GetCat")
        resp = client.get(f"/ecm/categories/{cat.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_list(self, client, auth_headers, db_session):
        _create_category(db_session, name=f"cat_{uuid.uuid4().hex[:6]}")
        resp = client.get("/ecm/categories", headers=auth_headers)
        assert resp.status_code == 200

    def test_update(self, client, auth_headers, db_session):
        cat = _create_category(db_session, name="OldCat")
        resp = client.patch(
            f"/ecm/categories/{cat.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_delete(self, client, auth_headers, db_session):
        cat = _create_category(db_session, name=f"cat_{uuid.uuid4().hex[:6]}")
        resp = client.delete(f"/ecm/categories/{cat.id}", headers=auth_headers)
        assert resp.status_code == 204


class TestDocumentCategoryEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        cat = _create_category(db_session)
        resp = client.post(
            "/ecm/document-categories",
            json={"document_id": str(doc.id), "category_id": str(cat.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_list(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        cat = _create_category(db_session)
        client.post(
            "/ecm/document-categories",
            json={"document_id": str(doc.id), "category_id": str(cat.id)},
            headers=auth_headers,
        )
        resp = client.get("/ecm/document-categories", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        cat = _create_category(db_session)
        create_resp = client.post(
            "/ecm/document-categories",
            json={"document_id": str(doc.id), "category_id": str(cat.id)},
            headers=auth_headers,
        )
        link_id = create_resp.json()["id"]
        resp = client.delete(
            f"/ecm/document-categories/{link_id}", headers=auth_headers
        )
        assert resp.status_code == 204
