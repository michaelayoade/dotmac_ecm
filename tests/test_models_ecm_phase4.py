import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.ecm import (
    Category,
    ContentType,
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentRetention,
    LegalHold,
    LegalHoldDocument,
    RetentionPolicy,
)
from app.models.person import Person


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"ecm-p4-{uuid.uuid4().hex}@example.com"


def _make_person(db_session: object) -> Person:
    p = Person(first_name="Ret", last_name="Tester", email=_unique_email())
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


def _make_content_type(db_session: object) -> ContentType:
    ct = ContentType(
        name=f"ct-{uuid.uuid4().hex[:8]}",
        description="Test content type",
    )
    db_session.add(ct)
    db_session.flush()
    return ct


def _make_category(db_session: object) -> Category:
    cat = Category(
        name=f"cat-{uuid.uuid4().hex[:8]}",
        path="/",
        depth=0,
    )
    db_session.add(cat)
    db_session.flush()
    return cat


def _make_retention_policy(
    db_session: object,
    disposition: DispositionAction = DispositionAction.archive,
    retention_days: int = 365,
) -> RetentionPolicy:
    rp = RetentionPolicy(
        name=f"policy-{uuid.uuid4().hex[:8]}",
        description="Test retention policy",
        retention_days=retention_days,
        disposition_action=disposition,
    )
    db_session.add(rp)
    db_session.flush()
    return rp


def _make_legal_hold(db_session: object, person: Person) -> LegalHold:
    lh = LegalHold(
        name=f"Hold-{uuid.uuid4().hex[:8]}",
        description="Test legal hold",
        reference_number=f"LH-{uuid.uuid4().hex[:6]}",
        created_by=person.id,
    )
    db_session.add(lh)
    db_session.flush()
    return lh


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestPhase4Enums:
    def test_disposition_action_values(self) -> None:
        assert DispositionAction.retain.value == "retain"
        assert DispositionAction.archive.value == "archive"
        assert DispositionAction.destroy.value == "destroy"
        assert len(DispositionAction) == 3

    def test_disposition_status_values(self) -> None:
        assert DispositionStatus.pending.value == "pending"
        assert DispositionStatus.eligible.value == "eligible"
        assert DispositionStatus.held.value == "held"
        assert DispositionStatus.completed.value == "completed"
        assert len(DispositionStatus) == 4


# ---------------------------------------------------------------------------
# RetentionPolicy Tests
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    def test_create_retention_policy(self, db_session: object) -> None:
        rp = _make_retention_policy(db_session)
        db_session.refresh(rp)

        assert rp.id is not None
        assert rp.name.startswith("policy-")
        assert rp.retention_days == 365
        assert rp.disposition_action == DispositionAction.archive
        assert rp.is_active is True
        assert rp.created_at is not None
        assert rp.updated_at is not None

    def test_unique_name_constraint(self, db_session: object) -> None:
        name = f"policy-unique-{uuid.uuid4().hex[:8]}"
        rp1 = RetentionPolicy(
            name=name,
            retention_days=30,
            disposition_action=DispositionAction.destroy,
        )
        db_session.add(rp1)
        db_session.flush()

        rp2 = RetentionPolicy(
            name=name,
            retention_days=60,
            disposition_action=DispositionAction.archive,
        )
        db_session.add(rp2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_all_disposition_actions(self, db_session: object) -> None:
        for action in DispositionAction:
            rp = RetentionPolicy(
                name=f"policy-{action.value}-{uuid.uuid4().hex[:8]}",
                retention_days=90,
                disposition_action=action,
            )
            db_session.add(rp)
        db_session.flush()

        policies = db_session.execute(select(RetentionPolicy)).scalars().all()
        actions = {p.disposition_action for p in policies}
        assert DispositionAction.retain in actions
        assert DispositionAction.archive in actions
        assert DispositionAction.destroy in actions

    def test_content_type_relationship(self, db_session: object) -> None:
        ct = _make_content_type(db_session)
        rp = RetentionPolicy(
            name=f"policy-ct-{uuid.uuid4().hex[:8]}",
            retention_days=180,
            disposition_action=DispositionAction.archive,
            content_type_id=ct.id,
        )
        db_session.add(rp)
        db_session.flush()
        db_session.refresh(rp)

        assert rp.content_type.id == ct.id

    def test_category_relationship(self, db_session: object) -> None:
        cat = _make_category(db_session)
        rp = RetentionPolicy(
            name=f"policy-cat-{uuid.uuid4().hex[:8]}",
            retention_days=730,
            disposition_action=DispositionAction.retain,
            category_id=cat.id,
        )
        db_session.add(rp)
        db_session.flush()
        db_session.refresh(rp)

        assert rp.category.id == cat.id

    def test_nullable_content_type_and_category(self, db_session: object) -> None:
        rp = _make_retention_policy(db_session)
        db_session.refresh(rp)

        assert rp.content_type_id is None
        assert rp.category_id is None

    def test_description_nullable(self, db_session: object) -> None:
        rp = RetentionPolicy(
            name=f"policy-{uuid.uuid4().hex[:8]}",
            retention_days=30,
            disposition_action=DispositionAction.destroy,
        )
        db_session.add(rp)
        db_session.flush()
        db_session.refresh(rp)

        assert rp.description is None


# ---------------------------------------------------------------------------
# DocumentRetention Tests
# ---------------------------------------------------------------------------


class TestDocumentRetention:
    def test_create_document_retention(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_retention_policy(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        dr = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=expires,
        )
        db_session.add(dr)
        db_session.flush()
        db_session.refresh(dr)

        assert dr.id is not None
        assert dr.document_id == doc.id
        assert dr.policy_id == policy.id
        assert dr.disposition_status == DispositionStatus.pending
        assert dr.disposed_at is None
        assert dr.disposed_by is None
        assert dr.is_active is True
        assert dr.created_at is not None

    def test_unique_constraint_doc_policy(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_retention_policy(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        dr1 = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=expires,
        )
        db_session.add(dr1)
        db_session.flush()

        dr2 = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=expires + timedelta(days=30),
        )
        db_session.add(dr2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_different_policies_same_document(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy1 = _make_retention_policy(db_session)
        policy2 = _make_retention_policy(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        dr1 = DocumentRetention(
            document_id=doc.id,
            policy_id=policy1.id,
            retention_expires_at=expires,
        )
        dr2 = DocumentRetention(
            document_id=doc.id,
            policy_id=policy2.id,
            retention_expires_at=expires,
        )
        db_session.add_all([dr1, dr2])
        db_session.flush()

        retentions = (
            db_session.execute(
                select(DocumentRetention).where(DocumentRetention.document_id == doc.id)
            )
            .scalars()
            .all()
        )
        assert len(retentions) == 2

    def test_all_disposition_statuses(self, db_session: object) -> None:
        person = _make_person(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        for status in DispositionStatus:
            doc = _make_document(db_session, person)
            policy = _make_retention_policy(db_session)
            dr = DocumentRetention(
                document_id=doc.id,
                policy_id=policy.id,
                retention_expires_at=expires,
                disposition_status=status,
            )
            db_session.add(dr)
        db_session.flush()

        retentions = db_session.execute(select(DocumentRetention)).scalars().all()
        statuses = {r.disposition_status for r in retentions}
        for status in DispositionStatus:
            assert status in statuses

    def test_disposition_completed_with_disposer(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_retention_policy(db_session)
        now = datetime.now(timezone.utc)

        dr = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=now - timedelta(days=1),
            disposition_status=DispositionStatus.completed,
            disposed_at=now,
            disposed_by=person.id,
        )
        db_session.add(dr)
        db_session.flush()
        db_session.refresh(dr)

        assert dr.disposition_status == DispositionStatus.completed
        assert dr.disposed_at is not None
        assert dr.disposed_by == person.id
        assert dr.disposer.id == person.id

    def test_document_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_retention_policy(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        dr = DocumentRetention(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=expires,
        )
        db_session.add(dr)
        db_session.flush()
        db_session.refresh(dr)

        assert dr.document.id == doc.id
        assert dr.policy.id == policy.id


# ---------------------------------------------------------------------------
# LegalHold Tests
# ---------------------------------------------------------------------------


class TestLegalHold:
    def test_create_legal_hold(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        db_session.refresh(lh)

        assert lh.id is not None
        assert lh.name.startswith("Hold-")
        assert lh.description == "Test legal hold"
        assert lh.reference_number is not None
        assert lh.created_by == person.id
        assert lh.is_active is True
        assert lh.created_at is not None
        assert lh.updated_at is not None

    def test_nullable_fields(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = LegalHold(
            name=f"Hold-{uuid.uuid4().hex[:8]}",
            created_by=person.id,
        )
        db_session.add(lh)
        db_session.flush()
        db_session.refresh(lh)

        assert lh.description is None
        assert lh.reference_number is None

    def test_creator_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        db_session.refresh(lh)

        assert lh.creator.id == person.id

    def test_documents_relationship(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        doc = _make_document(db_session, person)

        lhd = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd)
        db_session.flush()
        db_session.refresh(lh)

        assert len(lh.documents) == 1
        assert lh.documents[0].document_id == doc.id

    def test_multiple_holds(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh1 = _make_legal_hold(db_session, person)
        lh2 = _make_legal_hold(db_session, person)

        holds = db_session.execute(select(LegalHold)).scalars().all()
        hold_ids = {h.id for h in holds}
        assert lh1.id in hold_ids
        assert lh2.id in hold_ids


# ---------------------------------------------------------------------------
# LegalHoldDocument Tests
# ---------------------------------------------------------------------------


class TestLegalHoldDocument:
    def test_create_legal_hold_document(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        doc = _make_document(db_session, person)

        lhd = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd)
        db_session.flush()
        db_session.refresh(lhd)

        assert lhd.id is not None
        assert lhd.legal_hold_id == lh.id
        assert lhd.document_id == doc.id
        assert lhd.added_by == person.id
        assert lhd.created_at is not None

    def test_unique_constraint_hold_doc(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        doc = _make_document(db_session, person)

        lhd1 = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd1)
        db_session.flush()

        lhd2 = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_same_doc_different_holds(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh1 = _make_legal_hold(db_session, person)
        lh2 = _make_legal_hold(db_session, person)
        doc = _make_document(db_session, person)

        lhd1 = LegalHoldDocument(
            legal_hold_id=lh1.id,
            document_id=doc.id,
            added_by=person.id,
        )
        lhd2 = LegalHoldDocument(
            legal_hold_id=lh2.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add_all([lhd1, lhd2])
        db_session.flush()

        docs = (
            db_session.execute(
                select(LegalHoldDocument).where(LegalHoldDocument.document_id == doc.id)
            )
            .scalars()
            .all()
        )
        assert len(docs) == 2

    def test_same_hold_different_docs(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        doc1 = _make_document(db_session, person)
        doc2 = _make_document(db_session, person)

        lhd1 = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc1.id,
            added_by=person.id,
        )
        lhd2 = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc2.id,
            added_by=person.id,
        )
        db_session.add_all([lhd1, lhd2])
        db_session.flush()
        db_session.refresh(lh)

        assert len(lh.documents) == 2

    def test_relationships(self, db_session: object) -> None:
        person = _make_person(db_session)
        lh = _make_legal_hold(db_session, person)
        doc = _make_document(db_session, person)

        lhd = LegalHoldDocument(
            legal_hold_id=lh.id,
            document_id=doc.id,
            added_by=person.id,
        )
        db_session.add(lhd)
        db_session.flush()
        db_session.refresh(lhd)

        assert lhd.legal_hold.id == lh.id
        assert lhd.document.id == doc.id
        assert lhd.adder.id == person.id
