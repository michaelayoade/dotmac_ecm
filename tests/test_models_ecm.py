import uuid

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models.ecm import (
    Category,
    ClassificationLevel,
    ContentType,
    Document,
    DocumentCategory,
    DocumentStatus,
    DocumentTag,
    DocumentVersion,
    Folder,
    Tag,
)
from app.models.person import Person


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"ecm-test-{uuid.uuid4().hex}@example.com"


def _make_person(db_session: object) -> Person:
    p = Person(first_name="ECM", last_name="Tester", email=_unique_email())
    db_session.add(p)
    db_session.flush()
    return p


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_document_status_values(self) -> None:
        assert DocumentStatus.draft.value == "draft"
        assert DocumentStatus.active.value == "active"
        assert DocumentStatus.archived.value == "archived"
        assert DocumentStatus.deleted.value == "deleted"
        assert len(DocumentStatus) == 4

    def test_classification_level_values(self) -> None:
        assert ClassificationLevel.public.value == "public"
        assert ClassificationLevel.internal.value == "internal"
        assert ClassificationLevel.confidential.value == "confidential"
        assert ClassificationLevel.restricted.value == "restricted"
        assert len(ClassificationLevel) == 4


# ---------------------------------------------------------------------------
# Folder Tests
# ---------------------------------------------------------------------------


class TestFolder:
    def test_create_root_folder(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = Folder(
            name="Root Folder",
            created_by=person.id,
            path="/",
            depth=0,
        )
        db_session.add(folder)
        db_session.flush()
        db_session.refresh(folder)

        assert folder.id is not None
        assert folder.name == "Root Folder"
        assert folder.parent_id is None
        assert folder.path == "/"
        assert folder.depth == 0
        assert folder.is_active is True
        assert folder.created_at is not None
        assert folder.updated_at is not None

    def test_create_child_folder(self, db_session: object) -> None:
        person = _make_person(db_session)
        parent = Folder(name="Parent", created_by=person.id, path="/", depth=0)
        db_session.add(parent)
        db_session.flush()

        child = Folder(
            name="Child",
            parent_id=parent.id,
            created_by=person.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(child)
        db_session.flush()

        assert child.parent_id == parent.id
        assert child.depth == 1

    def test_folder_metadata(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = Folder(
            name="With Meta",
            created_by=person.id,
            path="/",
            depth=0,
            metadata_={"department": "engineering"},
        )
        db_session.add(folder)
        db_session.flush()
        db_session.refresh(folder)

        assert folder.metadata_ == {"department": "engineering"}

    def test_folder_unique_name_per_parent(self, db_session: object) -> None:
        person = _make_person(db_session)
        parent = Folder(name="UniqueParent", created_by=person.id, path="/", depth=0)
        db_session.add(parent)
        db_session.flush()

        f1 = Folder(
            name="Unique",
            parent_id=parent.id,
            created_by=person.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(f1)
        db_session.flush()

        f2 = Folder(
            name="Unique",
            parent_id=parent.id,
            created_by=person.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(f2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_folder_description_nullable(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = Folder(
            name="No Desc",
            created_by=person.id,
            path="/",
            depth=0,
        )
        db_session.add(folder)
        db_session.flush()
        db_session.refresh(folder)

        assert folder.description is None


# ---------------------------------------------------------------------------
# Document Tests
# ---------------------------------------------------------------------------


class TestDocument:
    def test_create_document(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Test Document",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        assert doc.id is not None
        assert doc.title == "Test Document"
        assert doc.status == DocumentStatus.draft
        assert doc.classification == ClassificationLevel.internal
        assert doc.version_number == 1
        assert doc.file_size == 1024
        assert doc.is_active is True
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_document_in_folder(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = Folder(name="Docs", created_by=person.id, path="/", depth=0)
        db_session.add(folder)
        db_session.flush()

        doc = Document(
            title="In Folder",
            folder_id=folder.id,
            file_name="report.docx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        assert doc.folder_id == folder.id

    def test_document_with_content_type(self, db_session: object) -> None:
        person = _make_person(db_session)
        ct = ContentType(name=f"Invoice-{uuid.uuid4().hex[:8]}")
        db_session.add(ct)
        db_session.flush()

        doc = Document(
            title="Typed Doc",
            content_type_id=ct.id,
            file_name="invoice.pdf",
            file_size=512,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        assert doc.content_type_id == ct.id

    def test_document_nullable_fields(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Minimal Doc",
            file_name="minimal.txt",
            file_size=0,
            mime_type="text/plain",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        assert doc.folder_id is None
        assert doc.content_type_id is None
        assert doc.description is None
        assert doc.storage_key is None
        assert doc.checksum_sha256 is None
        assert doc.current_version_id is None
        assert doc.metadata_ is None

    def test_document_status_enum(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Active Doc",
            file_name="active.pdf",
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.active,
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        assert doc.status == DocumentStatus.active

    def test_document_classification_enum(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Confidential Doc",
            file_name="secret.pdf",
            file_size=100,
            mime_type="application/pdf",
            classification=ClassificationLevel.confidential,
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        assert doc.classification == ClassificationLevel.confidential


# ---------------------------------------------------------------------------
# DocumentVersion Tests
# ---------------------------------------------------------------------------


class TestDocumentVersion:
    def test_create_version(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Versioned Doc",
            file_name="v1.pdf",
            file_size=1000,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_name="v1.pdf",
            file_size=1000,
            mime_type="application/pdf",
            storage_key="documents/test/1/abc/v1.pdf",
            checksum_sha256="a" * 64,
            created_by=person.id,
        )
        db_session.add(version)
        db_session.flush()
        db_session.refresh(version)

        assert version.id is not None
        assert version.version_number == 1
        assert version.file_size == 1000
        assert version.storage_key == "documents/test/1/abc/v1.pdf"
        assert version.is_active is True
        assert version.created_at is not None

    def test_version_immutability_no_updated_at(self) -> None:
        """DocumentVersion should not have an updated_at column."""
        mapper = inspect(DocumentVersion)
        column_names = [c.key for c in mapper.column_attrs]
        assert "updated_at" not in column_names

    def test_version_unique_per_document(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Dup Version Doc",
            file_name="dup.pdf",
            file_size=500,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        v1 = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_name="v1.pdf",
            file_size=500,
            mime_type="application/pdf",
            storage_key="documents/test/1/key1/v1.pdf",
            checksum_sha256="b" * 64,
            created_by=person.id,
        )
        db_session.add(v1)
        db_session.flush()

        v1_dup = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_name="v1-dup.pdf",
            file_size=500,
            mime_type="application/pdf",
            storage_key="documents/test/1/key2/v1-dup.pdf",
            checksum_sha256="c" * 64,
            created_by=person.id,
        )
        db_session.add(v1_dup)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_multiple_versions(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Multi Version Doc",
            file_name="multi.pdf",
            file_size=500,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        for i in range(1, 4):
            v = DocumentVersion(
                document_id=doc.id,
                version_number=i,
                file_name=f"v{i}.pdf",
                file_size=500 * i,
                mime_type="application/pdf",
                storage_key=f"documents/test/{i}/key/v{i}.pdf",
                checksum_sha256=str(i) * 64,
                created_by=person.id,
            )
            db_session.add(v)
        db_session.flush()

        versions = (
            db_session.execute(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == doc.id)
                .order_by(DocumentVersion.version_number)
            )
            .scalars()
            .all()
        )
        assert len(versions) == 3
        assert [v.version_number for v in versions] == [1, 2, 3]

    def test_version_change_summary_nullable(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Summary Test",
            file_name="s.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        v = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_name="s.pdf",
            file_size=100,
            mime_type="application/pdf",
            storage_key="documents/test/1/key/s.pdf",
            checksum_sha256="d" * 64,
            change_summary="Initial upload",
            created_by=person.id,
        )
        db_session.add(v)
        db_session.flush()
        db_session.refresh(v)

        assert v.change_summary == "Initial upload"


# ---------------------------------------------------------------------------
# ContentType Tests
# ---------------------------------------------------------------------------


class TestContentType:
    def test_create_content_type(self, db_session: object) -> None:
        ct = ContentType(
            name=f"Contract-{uuid.uuid4().hex[:8]}",
            description="Legal contracts",
            schema={"type": "object", "properties": {"party": {"type": "string"}}},
        )
        db_session.add(ct)
        db_session.flush()
        db_session.refresh(ct)

        assert ct.id is not None
        assert ct.is_active is True
        assert ct.schema is not None
        assert ct.schema["type"] == "object"

    def test_content_type_unique_name(self, db_session: object) -> None:
        name = f"UniqueType-{uuid.uuid4().hex[:8]}"
        ct1 = ContentType(name=name)
        db_session.add(ct1)
        db_session.flush()

        ct2 = ContentType(name=name)
        db_session.add(ct2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_content_type_schema_nullable(self, db_session: object) -> None:
        ct = ContentType(name=f"NoSchema-{uuid.uuid4().hex[:8]}")
        db_session.add(ct)
        db_session.flush()
        db_session.refresh(ct)

        assert ct.schema is None


# ---------------------------------------------------------------------------
# Tag + DocumentTag Tests
# ---------------------------------------------------------------------------


class TestTag:
    def test_create_tag(self, db_session: object) -> None:
        tag = Tag(name=f"urgent-{uuid.uuid4().hex[:8]}")
        db_session.add(tag)
        db_session.flush()
        db_session.refresh(tag)

        assert tag.id is not None
        assert tag.is_active is True
        assert tag.created_at is not None

    def test_tag_unique_name(self, db_session: object) -> None:
        name = f"dup-tag-{uuid.uuid4().hex[:8]}"
        t1 = Tag(name=name)
        db_session.add(t1)
        db_session.flush()

        t2 = Tag(name=name)
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_tag_document(self, db_session: object) -> None:
        person = _make_person(db_session)
        tag = Tag(name=f"tag-{uuid.uuid4().hex[:8]}")
        doc = Document(
            title="Tagged Doc",
            file_name="tagged.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([tag, doc])
        db_session.flush()

        dt = DocumentTag(document_id=doc.id, tag_id=tag.id)
        db_session.add(dt)
        db_session.flush()

        assert dt.id is not None
        assert dt.document_id == doc.id
        assert dt.tag_id == tag.id

    def test_document_tag_unique_constraint(self, db_session: object) -> None:
        person = _make_person(db_session)
        tag = Tag(name=f"tag-uq-{uuid.uuid4().hex[:8]}")
        doc = Document(
            title="Dup Tag Doc",
            file_name="dup-tag.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([tag, doc])
        db_session.flush()

        dt1 = DocumentTag(document_id=doc.id, tag_id=tag.id)
        db_session.add(dt1)
        db_session.flush()

        dt2 = DocumentTag(document_id=doc.id, tag_id=tag.id)
        db_session.add(dt2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


# ---------------------------------------------------------------------------
# Category + DocumentCategory Tests
# ---------------------------------------------------------------------------


class TestCategory:
    def test_create_root_category(self, db_session: object) -> None:
        cat = Category(name=f"Legal-{uuid.uuid4().hex[:8]}", path="/", depth=0)
        db_session.add(cat)
        db_session.flush()
        db_session.refresh(cat)

        assert cat.id is not None
        assert cat.parent_id is None
        assert cat.path == "/"
        assert cat.depth == 0
        assert cat.is_active is True

    def test_create_child_category(self, db_session: object) -> None:
        parent = Category(name=f"ParentCat-{uuid.uuid4().hex[:8]}", path="/", depth=0)
        db_session.add(parent)
        db_session.flush()

        child = Category(
            name=f"ChildCat-{uuid.uuid4().hex[:8]}",
            parent_id=parent.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(child)
        db_session.flush()

        assert child.parent_id == parent.id
        assert child.depth == 1

    def test_category_unique_name_per_parent(self, db_session: object) -> None:
        parent = Category(
            name=f"UniqueParentCat-{uuid.uuid4().hex[:8]}", path="/", depth=0
        )
        db_session.add(parent)
        db_session.flush()

        name = f"DupCat-{uuid.uuid4().hex[:8]}"
        c1 = Category(name=name, parent_id=parent.id, path=f"/{parent.id}/", depth=1)
        db_session.add(c1)
        db_session.flush()

        c2 = Category(name=name, parent_id=parent.id, path=f"/{parent.id}/", depth=1)
        db_session.add(c2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_document_category(self, db_session: object) -> None:
        person = _make_person(db_session)
        cat = Category(name=f"Cat-{uuid.uuid4().hex[:8]}", path="/", depth=0)
        doc = Document(
            title="Categorized Doc",
            file_name="cat.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([cat, doc])
        db_session.flush()

        dc = DocumentCategory(document_id=doc.id, category_id=cat.id)
        db_session.add(dc)
        db_session.flush()

        assert dc.id is not None
        assert dc.document_id == doc.id
        assert dc.category_id == cat.id

    def test_document_category_unique_constraint(self, db_session: object) -> None:
        person = _make_person(db_session)
        cat = Category(name=f"Cat-uq-{uuid.uuid4().hex[:8]}", path="/", depth=0)
        doc = Document(
            title="Dup Cat Doc",
            file_name="dup-cat.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([cat, doc])
        db_session.flush()

        dc1 = DocumentCategory(document_id=doc.id, category_id=cat.id)
        db_session.add(dc1)
        db_session.flush()

        dc2 = DocumentCategory(document_id=doc.id, category_id=cat.id)
        db_session.add(dc2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


# ---------------------------------------------------------------------------
# Relationship Tests
# ---------------------------------------------------------------------------


class TestRelationships:
    def test_folder_documents_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = Folder(name="RelFolder", created_by=person.id, path="/", depth=0)
        db_session.add(folder)
        db_session.flush()

        doc = Document(
            title="Rel Doc",
            folder_id=folder.id,
            file_name="rel.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(folder)

        assert len(folder.documents) == 1
        assert folder.documents[0].title == "Rel Doc"

    def test_folder_parent_child_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        parent = Folder(name="RelParent", created_by=person.id, path="/", depth=0)
        db_session.add(parent)
        db_session.flush()

        child = Folder(
            name="RelChild",
            parent_id=parent.id,
            created_by=person.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(child)
        db_session.flush()
        db_session.refresh(parent)

        assert len(parent.children) == 1
        assert child.parent.id == parent.id

    def test_document_tags_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        tag = Tag(name=f"rel-tag-{uuid.uuid4().hex[:8]}")
        doc = Document(
            title="Rel Tag Doc",
            file_name="rel-tag.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([tag, doc])
        db_session.flush()

        dt = DocumentTag(document_id=doc.id, tag_id=tag.id)
        db_session.add(dt)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.tags) == 1
        assert doc.tags[0].tag.name == tag.name

    def test_document_categories_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        cat = Category(name=f"rel-cat-{uuid.uuid4().hex[:8]}", path="/", depth=0)
        doc = Document(
            title="Rel Cat Doc",
            file_name="rel-cat.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add_all([cat, doc])
        db_session.flush()

        dc = DocumentCategory(document_id=doc.id, category_id=cat.id)
        db_session.add(dc)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.categories) == 1
        assert doc.categories[0].category.name == cat.name

    def test_document_version_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = Document(
            title="Version Rel Doc",
            file_name="vrel.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
        )
        db_session.add(doc)
        db_session.flush()

        v1 = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            file_name="vrel.pdf",
            file_size=100,
            mime_type="application/pdf",
            storage_key="documents/test/1/key/vrel.pdf",
            checksum_sha256="e" * 64,
            created_by=person.id,
        )
        db_session.add(v1)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.versions) == 1
        assert doc.versions[0].version_number == 1
        assert v1.document.id == doc.id

    def test_category_parent_child_relationship(self, db_session: object) -> None:
        parent = Category(
            name=f"RelParentCat-{uuid.uuid4().hex[:8]}", path="/", depth=0
        )
        db_session.add(parent)
        db_session.flush()

        child = Category(
            name=f"RelChildCat-{uuid.uuid4().hex[:8]}",
            parent_id=parent.id,
            path=f"/{parent.id}/",
            depth=1,
        )
        db_session.add(child)
        db_session.flush()
        db_session.refresh(parent)

        assert len(parent.children) == 1
        assert child.parent.id == parent.id
