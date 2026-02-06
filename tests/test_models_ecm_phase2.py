import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models.ecm import (
    ACLPermission,
    Document,
    DocumentACL,
    DocumentCheckout,
    Folder,
    FolderACL,
    PrincipalType,
)
from app.models.person import Person
from app.models.rbac import Role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"ecm-p2-{uuid.uuid4().hex}@example.com"


def _make_person(db_session: object) -> Person:
    p = Person(first_name="ACL", last_name="Tester", email=_unique_email())
    db_session.add(p)
    db_session.flush()
    return p


def _make_document(db_session: object, person: Person) -> Document:
    doc = Document(
        title=f"Doc-{uuid.uuid4().hex[:8]}",
        file_name="test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        created_by=person.id,
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def _make_folder(db_session: object, person: Person) -> Folder:
    folder = Folder(
        name=f"Folder-{uuid.uuid4().hex[:8]}",
        created_by=person.id,
        path="/",
        depth=0,
    )
    db_session.add(folder)
    db_session.flush()
    return folder


def _make_role(db_session: object) -> Role:
    role = Role(
        name=f"role-{uuid.uuid4().hex[:8]}",
        description="Test role",
    )
    db_session.add(role)
    db_session.flush()
    return role


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestPhase2Enums:
    def test_acl_permission_values(self) -> None:
        assert ACLPermission.read.value == "read"
        assert ACLPermission.write.value == "write"
        assert ACLPermission.delete.value == "delete"
        assert ACLPermission.manage.value == "manage"
        assert len(ACLPermission) == 4

    def test_principal_type_values(self) -> None:
        assert PrincipalType.person.value == "person"
        assert PrincipalType.role.value == "role"
        assert len(PrincipalType) == 2


# ---------------------------------------------------------------------------
# DocumentACL Tests
# ---------------------------------------------------------------------------


class TestDocumentACL:
    def test_create_person_acl(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        acl = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.id is not None
        assert acl.principal_type == PrincipalType.person
        assert acl.permission == ACLPermission.read
        assert acl.is_active is True
        assert acl.created_at is not None

    def test_create_role_acl(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        role = _make_role(db_session)

        acl = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.role,
            principal_id=role.id,
            permission=ACLPermission.write,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.principal_type == PrincipalType.role
        assert acl.principal_id == role.id
        assert acl.permission == ACLPermission.write

    def test_multiple_permissions_same_principal(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        for perm in [ACLPermission.read, ACLPermission.write, ACLPermission.delete]:
            acl = DocumentACL(
                document_id=doc.id,
                principal_type=PrincipalType.person,
                principal_id=person.id,
                permission=perm,
                granted_by=person.id,
            )
            db_session.add(acl)
        db_session.flush()

        acls = (
            db_session.execute(
                select(DocumentACL).where(DocumentACL.document_id == doc.id)
            )
            .scalars()
            .all()
        )
        assert len(acls) == 3

    def test_unique_constraint_prevents_duplicate(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        acl1 = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            granted_by=person.id,
        )
        db_session.add(acl1)
        db_session.flush()

        acl2 = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            granted_by=person.id,
        )
        db_session.add(acl2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_document_acls_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        acl = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.manage,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(doc)

        assert len(doc.acls) == 1
        assert doc.acls[0].permission == ACLPermission.manage

    def test_grantor_relationship(self, db_session: object) -> None:
        granter = _make_person(db_session)
        grantee = _make_person(db_session)
        doc = _make_document(db_session, granter)

        acl = DocumentACL(
            document_id=doc.id,
            principal_type=PrincipalType.person,
            principal_id=grantee.id,
            permission=ACLPermission.read,
            granted_by=granter.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.grantor.id == granter.id


# ---------------------------------------------------------------------------
# FolderACL Tests
# ---------------------------------------------------------------------------


class TestFolderACL:
    def test_create_folder_acl(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        acl = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.id is not None
        assert acl.is_inherited is False
        assert acl.is_active is True
        assert acl.created_at is not None

    def test_inherited_flag(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        acl = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            is_inherited=True,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.is_inherited is True

    def test_role_principal(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)
        role = _make_role(db_session)

        acl = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.role,
            principal_id=role.id,
            permission=ACLPermission.manage,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(acl)

        assert acl.principal_type == PrincipalType.role
        assert acl.principal_id == role.id

    def test_unique_constraint_prevents_duplicate(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        acl1 = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.write,
            granted_by=person.id,
        )
        db_session.add(acl1)
        db_session.flush()

        acl2 = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.write,
            granted_by=person.id,
        )
        db_session.add(acl2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_folder_acls_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        acl = FolderACL(
            folder_id=folder.id,
            principal_type=PrincipalType.person,
            principal_id=person.id,
            permission=ACLPermission.read,
            granted_by=person.id,
        )
        db_session.add(acl)
        db_session.flush()
        db_session.refresh(folder)

        assert len(folder.acls) == 1
        assert folder.acls[0].permission == ACLPermission.read

    def test_same_principal_different_permissions(self, db_session: object) -> None:
        person = _make_person(db_session)
        folder = _make_folder(db_session, person)

        for perm in ACLPermission:
            acl = FolderACL(
                folder_id=folder.id,
                principal_type=PrincipalType.person,
                principal_id=person.id,
                permission=perm,
                granted_by=person.id,
            )
            db_session.add(acl)
        db_session.flush()

        acls = (
            db_session.execute(
                select(FolderACL).where(FolderACL.folder_id == folder.id)
            )
            .scalars()
            .all()
        )
        assert len(acls) == 4


# ---------------------------------------------------------------------------
# DocumentCheckout Tests
# ---------------------------------------------------------------------------


class TestDocumentCheckout:
    def test_create_checkout(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        checkout = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person.id,
            reason="Editing quarterly report",
        )
        db_session.add(checkout)
        db_session.flush()
        db_session.refresh(checkout)

        assert checkout.id is not None
        assert checkout.document_id == doc.id
        assert checkout.checked_out_by == person.id
        assert checkout.checked_out_at is not None
        assert checkout.reason == "Editing quarterly report"

    def test_checkout_reason_nullable(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        checkout = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person.id,
        )
        db_session.add(checkout)
        db_session.flush()
        db_session.refresh(checkout)

        assert checkout.reason is None

    def test_exclusive_checkout_unique_constraint(self, db_session: object) -> None:
        person1 = _make_person(db_session)
        person2 = _make_person(db_session)
        doc = _make_document(db_session, person1)

        co1 = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person1.id,
        )
        db_session.add(co1)
        db_session.flush()

        co2 = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person2.id,
        )
        db_session.add(co2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_hard_delete_on_checkin(self, db_session: object) -> None:
        """Checkouts are hard-deleted on check-in, not soft-deleted."""
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        checkout = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person.id,
        )
        db_session.add(checkout)
        db_session.flush()

        # Verify exists
        rows = (
            db_session.execute(
                select(DocumentCheckout).where(DocumentCheckout.document_id == doc.id)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

        # Hard delete (simulating check-in)
        db_session.execute(
            delete(DocumentCheckout).where(DocumentCheckout.document_id == doc.id)
        )
        db_session.flush()

        # Verify gone
        rows = (
            db_session.execute(
                select(DocumentCheckout).where(DocumentCheckout.document_id == doc.id)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 0

    def test_checkout_after_checkin(self, db_session: object) -> None:
        """After hard-deleting a checkout, a new checkout can be created."""
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        # First checkout
        co1 = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person.id,
        )
        db_session.add(co1)
        db_session.flush()

        # Check-in (hard delete)
        db_session.execute(
            delete(DocumentCheckout).where(DocumentCheckout.document_id == doc.id)
        )
        db_session.flush()

        # Second checkout by different person should succeed
        person2 = _make_person(db_session)
        co2 = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person2.id,
        )
        db_session.add(co2)
        db_session.flush()
        db_session.refresh(co2)

        assert co2.checked_out_by == person2.id

    def test_different_documents_checkout(self, db_session: object) -> None:
        """Different documents can be checked out simultaneously."""
        person = _make_person(db_session)
        doc1 = _make_document(db_session, person)
        doc2 = _make_document(db_session, person)

        co1 = DocumentCheckout(document_id=doc1.id, checked_out_by=person.id)
        co2 = DocumentCheckout(document_id=doc2.id, checked_out_by=person.id)
        db_session.add_all([co1, co2])
        db_session.flush()

        checkouts = db_session.execute(select(DocumentCheckout)).scalars().all()
        doc_ids = {co.document_id for co in checkouts}
        assert doc1.id in doc_ids
        assert doc2.id in doc_ids

    def test_document_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)

        checkout = DocumentCheckout(
            document_id=doc.id,
            checked_out_by=person.id,
        )
        db_session.add(checkout)
        db_session.flush()
        db_session.refresh(checkout)

        assert checkout.document.id == doc.id
        assert checkout.person.id == person.id
