import uuid

from app.models.ecm import (
    ClassificationLevel,
    Comment,
    CommentStatus,
    Document,
    DocumentStatus,
    DocumentSubscription,
    Folder,
)
from app.models.person import Person


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="Collab",
        email=f"api-collab-{uuid.uuid4().hex[:8]}@test.com",
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


def _create_comment(db_session, person, doc=None):
    if doc is None:
        doc = _create_document(db_session, person)
    comment = Comment(
        document_id=doc.id,
        body="Test comment",
        author_id=person.id,
        status=CommentStatus.active,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


class TestCommentEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/comments",
            json={
                "document_id": str(doc.id),
                "body": "Hello world",
                "author_id": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == "Hello world"
        assert data["status"] == "active"

    def test_create_with_parent(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        parent = _create_comment(db_session, person, doc=doc)
        resp = client.post(
            "/ecm/comments",
            json={
                "document_id": str(doc.id),
                "body": "Reply",
                "author_id": str(person.id),
                "parent_id": str(parent.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["parent_id"] == str(parent.id)

    def test_create_invalid_document(self, client, auth_headers, db_session, person):
        resp = client.post(
            "/ecm/comments",
            json={
                "document_id": str(uuid.uuid4()),
                "body": "Hello",
                "author_id": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        comment = _create_comment(db_session, person)
        resp = client.get(
            f"/ecm/comments/{comment.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(comment.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/comments/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session, person):
        _create_comment(db_session, person)
        resp = client.get("/ecm/comments", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 1

    def test_list_filter_by_document(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        _create_comment(db_session, person, doc=doc)
        resp = client.get(
            f"/ecm/comments?document_id={doc.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_update(self, client, auth_headers, db_session, person):
        comment = _create_comment(db_session, person)
        resp = client.patch(
            f"/ecm/comments/{comment.id}",
            json={"body": "Updated body"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "Updated body"

    def test_delete(self, client, auth_headers, db_session, person):
        comment = _create_comment(db_session, person)
        resp = client.delete(
            f"/ecm/comments/{comment.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestDocumentSubscriptionEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/document-subscriptions",
            json={
                "document_id": str(doc.id),
                "person_id": str(person.id),
                "event_types": ["comment", "version"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_types"] == ["comment", "version"]
        assert data["is_active"] is True

    def test_create_invalid_document(self, client, auth_headers, db_session, person):
        resp = client.post(
            "/ecm/document-subscriptions",
            json={
                "document_id": str(uuid.uuid4()),
                "person_id": str(person.id),
                "event_types": ["comment"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        resp = client.get(
            f"/ecm/document-subscriptions/{sub.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(sub.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/document-subscriptions/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        resp = client.get("/ecm/document-subscriptions", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        resp = client.patch(
            f"/ecm/document-subscriptions/{sub.id}",
            json={"event_types": ["comment", "version"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["event_types"] == ["comment", "version"]

    def test_delete(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        resp = client.delete(
            f"/ecm/document-subscriptions/{sub.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204
