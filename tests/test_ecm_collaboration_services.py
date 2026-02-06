import uuid

import pytest
from fastapi import HTTPException

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
from app.schemas.ecm_collaboration import (
    CommentCreate,
    CommentUpdate,
    DocumentSubscriptionCreate,
    DocumentSubscriptionUpdate,
)
from app.services.ecm_collaboration import Comments, DocumentSubscriptions


def _make_person(db_session):
    p = Person(
        first_name="Collab",
        last_name="Tester",
        email=f"collab-{uuid.uuid4().hex[:8]}@test.com",
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


def _make_comment(db_session, person, doc=None, parent_id=None):
    if doc is None:
        doc = _make_document(db_session, person)
    comment = Comment(
        document_id=doc.id,
        body="Test comment",
        author_id=person.id,
        parent_id=parent_id,
        status=CommentStatus.active,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


class TestComments:
    def test_create(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = CommentCreate(
            document_id=doc.id,
            body="Hello world",
            author_id=person.id,
        )
        comment = Comments.create(db_session, payload)
        assert comment.document_id == doc.id
        assert comment.body == "Hello world"
        assert comment.author_id == person.id
        assert comment.status == CommentStatus.active
        assert comment.is_active is True

    def test_create_with_parent(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        parent = _make_comment(db_session, person, doc=doc)
        payload = CommentCreate(
            document_id=doc.id,
            body="Reply",
            author_id=person.id,
            parent_id=parent.id,
        )
        reply = Comments.create(db_session, payload)
        assert reply.parent_id == parent.id

    def test_create_invalid_document(self, db_session):
        person = _make_person(db_session)
        payload = CommentCreate(
            document_id=uuid.uuid4(),
            body="Hello",
            author_id=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            Comments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_author(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = CommentCreate(
            document_id=doc.id,
            body="Hello",
            author_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            Comments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Author not found" in exc.value.detail

    def test_create_invalid_parent(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = CommentCreate(
            document_id=doc.id,
            body="Reply",
            author_id=person.id,
            parent_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            Comments.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Parent comment not found" in exc.value.detail

    def test_create_parent_different_document(self, db_session):
        person = _make_person(db_session)
        doc1 = _make_document(db_session, person)
        doc2 = _make_document(db_session, person)
        parent = _make_comment(db_session, person, doc=doc1)
        payload = CommentCreate(
            document_id=doc2.id,
            body="Cross-doc reply",
            author_id=person.id,
            parent_id=parent.id,
        )
        with pytest.raises(HTTPException) as exc:
            Comments.create(db_session, payload)
        assert exc.value.status_code == 400
        assert "different document" in exc.value.detail

    def test_create_invalid_status(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = CommentCreate(
            document_id=doc.id,
            body="Hello",
            author_id=person.id,
            status="invalid",
        )
        with pytest.raises(HTTPException) as exc:
            Comments.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_get(self, db_session):
        person = _make_person(db_session)
        comment = _make_comment(db_session, person)
        found = Comments.get(db_session, str(comment.id))
        assert found.id == comment.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Comments.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_document(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        _make_comment(db_session, person, doc=doc)
        results = Comments.list(
            db_session,
            document_id=str(doc.id),
            author_id=None,
            parent_id=None,
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.document_id == doc.id for r in results)

    def test_list_filter_by_author(self, db_session):
        person = _make_person(db_session)
        _make_comment(db_session, person)
        results = Comments.list(
            db_session,
            document_id=None,
            author_id=str(person.id),
            parent_id=None,
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.author_id == person.id for r in results)

    def test_list_filter_by_parent(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        parent = _make_comment(db_session, person, doc=doc)
        _make_comment(db_session, person, doc=doc, parent_id=parent.id)
        results = Comments.list(
            db_session,
            document_id=None,
            author_id=None,
            parent_id=str(parent.id),
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.parent_id == parent.id for r in results)

    def test_update(self, db_session):
        person = _make_person(db_session)
        comment = _make_comment(db_session, person)
        updated = Comments.update(
            db_session,
            str(comment.id),
            CommentUpdate(body="Updated body"),
        )
        assert updated.body == "Updated body"

    def test_update_status(self, db_session):
        person = _make_person(db_session)
        comment = _make_comment(db_session, person)
        updated = Comments.update(
            db_session,
            str(comment.id),
            CommentUpdate(status="deleted"),
        )
        assert updated.status == CommentStatus.deleted

    def test_update_invalid_status(self, db_session):
        person = _make_person(db_session)
        comment = _make_comment(db_session, person)
        with pytest.raises(HTTPException) as exc:
            Comments.update(
                db_session,
                str(comment.id),
                CommentUpdate(status="invalid"),
            )
        assert exc.value.status_code == 400

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        comment = _make_comment(db_session, person)
        Comments.delete(db_session, str(comment.id))
        db_session.refresh(comment)
        assert comment.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Comments.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestDocumentSubscriptions:
    def test_create(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentSubscriptionCreate(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment", "version"],
        )
        sub = DocumentSubscriptions.create(db_session, payload)
        assert sub.document_id == doc.id
        assert sub.person_id == person.id
        assert sub.event_types == ["comment", "version"]
        assert sub.is_active is True

    def test_create_invalid_document(self, db_session):
        person = _make_person(db_session)
        payload = DocumentSubscriptionCreate(
            document_id=uuid.uuid4(),
            person_id=person.id,
            event_types=["comment"],
        )
        with pytest.raises(HTTPException) as exc:
            DocumentSubscriptions.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_person(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentSubscriptionCreate(
            document_id=doc.id,
            person_id=uuid.uuid4(),
            event_types=["comment"],
        )
        with pytest.raises(HTTPException) as exc:
            DocumentSubscriptions.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Person not found" in exc.value.detail

    def test_get(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        found = DocumentSubscriptions.get(db_session, str(sub.id))
        assert found.id == sub.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentSubscriptions.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_document(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        results = DocumentSubscriptions.list(
            db_session,
            document_id=str(doc.id),
            person_id=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.document_id == doc.id for r in results)

    def test_list_filter_by_person(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        results = DocumentSubscriptions.list(
            db_session,
            document_id=None,
            person_id=str(person.id),
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.person_id == person.id for r in results)

    def test_update(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        updated = DocumentSubscriptions.update(
            db_session,
            str(sub.id),
            DocumentSubscriptionUpdate(event_types=["comment", "version", "status"]),
        )
        assert updated.event_types == ["comment", "version", "status"]

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        sub = DocumentSubscription(
            document_id=doc.id,
            person_id=person.id,
            event_types=["comment"],
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        DocumentSubscriptions.delete(db_session, str(sub.id))
        db_session.refresh(sub)
        assert sub.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentSubscriptions.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404
