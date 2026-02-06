import uuid

import pytest
from fastapi import HTTPException

from app.schemas.ecm import (
    CategoryCreate,
    CategoryUpdate,
    ContentTypeCreate,
    ContentTypeUpdate,
    DocumentCategoryCreate,
    DocumentCreate,
    DocumentTagCreate,
    TagCreate,
    TagUpdate,
)
from app.services.ecm_document import Documents
from app.services.ecm_metadata import (
    Categories,
    ContentTypes,
    DocumentCategories,
    DocumentTags,
    Tags,
)


def _make_doc(db_session, person):

    payload = DocumentCreate(
        title="Test Doc",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
    )
    return Documents.create(db_session, payload)


class TestContentTypes:
    def test_create(self, db_session):
        payload = ContentTypeCreate(
            name=f"Invoice_{uuid.uuid4().hex[:6]}",
            description="Invoice documents",
        )
        ct = ContentTypes.create(db_session, payload)
        assert ct.name == payload.name
        assert ct.is_active is True

    def test_get(self, db_session):
        ct = ContentTypes.create(
            db_session,
            ContentTypeCreate(name=f"CT_{uuid.uuid4().hex[:6]}"),
        )
        found = ContentTypes.get(db_session, str(ct.id))
        assert found.id == ct.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            ContentTypes.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list(self, db_session):
        ContentTypes.create(
            db_session,
            ContentTypeCreate(name=f"CT_{uuid.uuid4().hex[:6]}"),
        )
        results = ContentTypes.list(
            db_session,
            is_active=None,
            order_by="name",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        ct = ContentTypes.create(
            db_session,
            ContentTypeCreate(name=f"CT_{uuid.uuid4().hex[:6]}"),
        )
        updated = ContentTypes.update(
            db_session,
            str(ct.id),
            ContentTypeUpdate(description="Updated"),
        )
        assert updated.description == "Updated"

    def test_soft_delete(self, db_session):
        ct = ContentTypes.create(
            db_session,
            ContentTypeCreate(name=f"CT_{uuid.uuid4().hex[:6]}"),
        )
        ContentTypes.delete(db_session, str(ct.id))
        db_session.refresh(ct)
        assert ct.is_active is False


class TestTags:
    def test_create(self, db_session):
        tag = Tags.create(
            db_session,
            TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"),
        )
        assert tag.is_active is True

    def test_get(self, db_session):
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        found = Tags.get(db_session, str(tag.id))
        assert found.id == tag.id

    def test_update(self, db_session):
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        updated = Tags.update(db_session, str(tag.id), TagUpdate(description="Updated"))
        assert updated.description == "Updated"

    def test_soft_delete(self, db_session):
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        Tags.delete(db_session, str(tag.id))
        db_session.refresh(tag)
        assert tag.is_active is False


class TestDocumentTags:
    def test_create(self, db_session, person):
        doc = _make_doc(db_session, person)
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        link = DocumentTags.create(
            db_session,
            DocumentTagCreate(document_id=doc.id, tag_id=tag.id),
        )
        assert link.document_id == doc.id
        assert link.tag_id == tag.id

    def test_create_invalid_document(self, db_session):
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        with pytest.raises(HTTPException) as exc:
            DocumentTags.create(
                db_session,
                DocumentTagCreate(document_id=uuid.uuid4(), tag_id=tag.id),
            )
        assert exc.value.status_code == 404

    def test_create_invalid_tag(self, db_session, person):
        doc = _make_doc(db_session, person)
        with pytest.raises(HTTPException) as exc:
            DocumentTags.create(
                db_session,
                DocumentTagCreate(document_id=doc.id, tag_id=uuid.uuid4()),
            )
        assert exc.value.status_code == 404

    def test_list_by_document(self, db_session, person):
        doc = _make_doc(db_session, person)
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        DocumentTags.create(
            db_session,
            DocumentTagCreate(document_id=doc.id, tag_id=tag.id),
        )
        results = DocumentTags.list(
            db_session,
            document_id=str(doc.id),
            tag_id=None,
            order_by="document_id",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_delete(self, db_session, person):
        doc = _make_doc(db_session, person)
        tag = Tags.create(db_session, TagCreate(name=f"tag_{uuid.uuid4().hex[:6]}"))
        link = DocumentTags.create(
            db_session,
            DocumentTagCreate(document_id=doc.id, tag_id=tag.id),
        )
        DocumentTags.delete(db_session, str(link.id))
        with pytest.raises(HTTPException):
            DocumentTags.get(db_session, str(link.id))


class TestCategories:
    def test_create_root(self, db_session):
        cat = Categories.create(
            db_session,
            CategoryCreate(name=f"cat_{uuid.uuid4().hex[:6]}"),
        )
        assert cat.path.startswith("/")
        assert cat.depth == 0

    def test_create_child(self, db_session):
        parent = Categories.create(db_session, CategoryCreate(name="Parent"))
        child = Categories.create(
            db_session,
            CategoryCreate(name="Child", parent_id=parent.id),
        )
        assert child.path == f"{parent.path}/Child"
        assert child.depth == 1

    def test_update_move_recomputes(self, db_session):
        a = Categories.create(db_session, CategoryCreate(name="CatA"))
        b = Categories.create(db_session, CategoryCreate(name="CatB", parent_id=a.id))
        c = Categories.create(db_session, CategoryCreate(name="CatC", parent_id=b.id))
        new_root = Categories.create(db_session, CategoryCreate(name="NewRoot"))
        Categories.update(
            db_session,
            str(b.id),
            CategoryUpdate(parent_id=new_root.id),
        )
        db_session.refresh(c)
        assert c.path == "/NewRoot/CatB/CatC"

    def test_soft_delete(self, db_session):
        cat = Categories.create(
            db_session,
            CategoryCreate(name=f"cat_{uuid.uuid4().hex[:6]}"),
        )
        Categories.delete(db_session, str(cat.id))
        db_session.refresh(cat)
        assert cat.is_active is False


class TestDocumentCategories:
    def test_create(self, db_session, person):
        doc = _make_doc(db_session, person)
        cat = Categories.create(
            db_session,
            CategoryCreate(name=f"cat_{uuid.uuid4().hex[:6]}"),
        )
        link = DocumentCategories.create(
            db_session,
            DocumentCategoryCreate(document_id=doc.id, category_id=cat.id),
        )
        assert link.document_id == doc.id

    def test_create_invalid_document(self, db_session):
        cat = Categories.create(
            db_session,
            CategoryCreate(name=f"cat_{uuid.uuid4().hex[:6]}"),
        )
        with pytest.raises(HTTPException) as exc:
            DocumentCategories.create(
                db_session,
                DocumentCategoryCreate(document_id=uuid.uuid4(), category_id=cat.id),
            )
        assert exc.value.status_code == 404

    def test_delete(self, db_session, person):
        doc = _make_doc(db_session, person)
        cat = Categories.create(
            db_session,
            CategoryCreate(name=f"cat_{uuid.uuid4().hex[:6]}"),
        )
        link = DocumentCategories.create(
            db_session,
            DocumentCategoryCreate(document_id=doc.id, category_id=cat.id),
        )
        DocumentCategories.delete(db_session, str(link.id))
        with pytest.raises(HTTPException):
            DocumentCategories.get(db_session, str(link.id))
