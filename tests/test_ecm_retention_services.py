import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.ecm import (
    Category,
    ClassificationLevel,
    ContentType,
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentRetention,
    DocumentStatus,
    Folder,
    RetentionPolicy,
)
from app.models.person import Person
from app.schemas.ecm_retention import (
    DocumentRetentionCreate,
    DocumentRetentionUpdate,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
)
from app.services.ecm_retention import (
    DocumentRetentions,
    RetentionPolicies,
)


def _make_person(db_session):
    p = Person(
        first_name="Ret",
        last_name="Tester",
        email=f"ret-{uuid.uuid4().hex[:8]}@test.com",
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


def _make_content_type(db_session):
    ct = ContentType(name=f"ct_{uuid.uuid4().hex[:8]}")
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return ct


def _make_category(db_session):
    cat = Category(
        name=f"cat_{uuid.uuid4().hex[:8]}",
        path=f"/cat_{uuid.uuid4().hex[:8]}",
        depth=0,
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _make_policy(db_session, content_type=None, category=None):
    policy = RetentionPolicy(
        name=f"policy_{uuid.uuid4().hex[:8]}",
        description="Test retention policy",
        retention_days=365,
        disposition_action=DispositionAction.archive,
        content_type_id=content_type.id if content_type else None,
        category_id=category.id if category else None,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


def _make_retention(db_session, person, policy=None):
    if policy is None:
        policy = _make_policy(db_session)
    doc = _make_document(db_session, person)
    retention = DocumentRetention(
        document_id=doc.id,
        policy_id=policy.id,
        retention_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        disposition_status=DispositionStatus.pending,
    )
    db_session.add(retention)
    db_session.commit()
    db_session.refresh(retention)
    return retention


class TestRetentionPolicies:
    def test_create(self, db_session):
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            description="Test policy",
            retention_days=365,
            disposition_action="archive",
        )
        policy = RetentionPolicies.create(db_session, payload)
        assert policy.name == payload.name
        assert policy.retention_days == 365
        assert policy.disposition_action == DispositionAction.archive
        assert policy.is_active is True

    def test_create_with_content_type(self, db_session):
        ct = _make_content_type(db_session)
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=90,
            disposition_action="retain",
            content_type_id=ct.id,
        )
        policy = RetentionPolicies.create(db_session, payload)
        assert policy.content_type_id == ct.id

    def test_create_with_category(self, db_session):
        cat = _make_category(db_session)
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=180,
            disposition_action="destroy",
            category_id=cat.id,
        )
        policy = RetentionPolicies.create(db_session, payload)
        assert policy.category_id == cat.id

    def test_create_invalid_disposition_action(self, db_session):
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=365,
            disposition_action="invalid",
        )
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_create_invalid_content_type(self, db_session):
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=365,
            disposition_action="archive",
            content_type_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Content type not found" in exc.value.detail

    def test_create_invalid_category(self, db_session):
        payload = RetentionPolicyCreate(
            name=f"policy_{uuid.uuid4().hex[:8]}",
            retention_days=365,
            disposition_action="archive",
            category_id=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Category not found" in exc.value.detail

    def test_get(self, db_session):
        policy = _make_policy(db_session)
        found = RetentionPolicies.get(db_session, str(policy.id))
        assert found.id == policy.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_default_active(self, db_session):
        policy = _make_policy(db_session)
        results = RetentionPolicies.list(
            db_session,
            disposition_action=None,
            content_type_id=None,
            category_id=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert policy.id in ids

    def test_list_filter_inactive(self, db_session):
        policy = _make_policy(db_session)
        policy.is_active = False
        db_session.commit()
        results = RetentionPolicies.list(
            db_session,
            disposition_action=None,
            content_type_id=None,
            category_id=None,
            is_active=False,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert policy.id in ids

    def test_list_filter_by_disposition_action(self, db_session):
        policy = _make_policy(db_session)
        results = RetentionPolicies.list(
            db_session,
            disposition_action="archive",
            content_type_id=None,
            category_id=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert policy.id in ids

    def test_list_filter_by_content_type(self, db_session):
        ct = _make_content_type(db_session)
        policy = _make_policy(db_session, content_type=ct)
        results = RetentionPolicies.list(
            db_session,
            disposition_action=None,
            content_type_id=str(ct.id),
            category_id=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert policy.id in ids

    def test_list_filter_by_category(self, db_session):
        cat = _make_category(db_session)
        policy = _make_policy(db_session, category=cat)
        results = RetentionPolicies.list(
            db_session,
            disposition_action=None,
            content_type_id=None,
            category_id=str(cat.id),
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert policy.id in ids

    def test_list_order_by_name(self, db_session):
        _make_policy(db_session)
        results = RetentionPolicies.list(
            db_session,
            disposition_action=None,
            content_type_id=None,
            category_id=None,
            is_active=None,
            order_by="name",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        policy = _make_policy(db_session)
        updated = RetentionPolicies.update(
            db_session,
            str(policy.id),
            RetentionPolicyUpdate(description="Updated"),
        )
        assert updated.description == "Updated"

    def test_update_disposition_action(self, db_session):
        policy = _make_policy(db_session)
        updated = RetentionPolicies.update(
            db_session,
            str(policy.id),
            RetentionPolicyUpdate(disposition_action="destroy"),
        )
        assert updated.disposition_action == DispositionAction.destroy

    def test_update_invalid_disposition_action(self, db_session):
        policy = _make_policy(db_session)
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.update(
                db_session,
                str(policy.id),
                RetentionPolicyUpdate(disposition_action="invalid"),
            )
        assert exc.value.status_code == 400

    def test_update_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.update(
                db_session,
                str(uuid.uuid4()),
                RetentionPolicyUpdate(description="x"),
            )
        assert exc.value.status_code == 404

    def test_soft_delete(self, db_session):
        policy = _make_policy(db_session)
        RetentionPolicies.delete(db_session, str(policy.id))
        db_session.refresh(policy)
        assert policy.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            RetentionPolicies.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestDocumentRetentions:
    def test_create(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_policy(db_session)
        payload = DocumentRetentionCreate(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            disposition_status="pending",
        )
        retention = DocumentRetentions.create(db_session, payload)
        assert retention.document_id == doc.id
        assert retention.policy_id == policy.id
        assert retention.disposition_status == DispositionStatus.pending
        assert retention.is_active is True

    def test_create_invalid_document(self, db_session):
        policy = _make_policy(db_session)
        payload = DocumentRetentionCreate(
            document_id=uuid.uuid4(),
            policy_id=policy.id,
            retention_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_policy(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = DocumentRetentionCreate(
            document_id=doc.id,
            policy_id=uuid.uuid4(),
            retention_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Retention policy not found" in exc.value.detail

    def test_create_invalid_disposition_status(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        policy = _make_policy(db_session)
        payload = DocumentRetentionCreate(
            document_id=doc.id,
            policy_id=policy.id,
            retention_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            disposition_status="invalid",
        )
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_get(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        found = DocumentRetentions.get(db_session, str(retention.id))
        assert found.id == retention.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_default_active(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        results = DocumentRetentions.list(
            db_session,
            document_id=None,
            policy_id=None,
            disposition_status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert retention.id in ids

    def test_list_filter_by_document(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        results = DocumentRetentions.list(
            db_session,
            document_id=str(retention.document_id),
            policy_id=None,
            disposition_status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.document_id == retention.document_id for r in results)

    def test_list_filter_by_policy(self, db_session):
        person = _make_person(db_session)
        policy = _make_policy(db_session)
        retention = _make_retention(db_session, person, policy=policy)
        results = DocumentRetentions.list(
            db_session,
            document_id=None,
            policy_id=str(policy.id),
            disposition_status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert retention.id in ids

    def test_list_filter_by_disposition_status(self, db_session):
        person = _make_person(db_session)
        _make_retention(db_session, person)
        results = DocumentRetentions.list(
            db_session,
            document_id=None,
            policy_id=None,
            disposition_status="pending",
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_list_order_by_retention_expires_at(self, db_session):
        person = _make_person(db_session)
        _make_retention(db_session, person)
        results = DocumentRetentions.list(
            db_session,
            document_id=None,
            policy_id=None,
            disposition_status=None,
            is_active=None,
            order_by="retention_expires_at",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        updated = DocumentRetentions.update(
            db_session,
            str(retention.id),
            DocumentRetentionUpdate(disposition_status="eligible"),
        )
        assert updated.disposition_status == DispositionStatus.eligible

    def test_update_invalid_disposition_status(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.update(
                db_session,
                str(retention.id),
                DocumentRetentionUpdate(disposition_status="invalid"),
            )
        assert exc.value.status_code == 400

    def test_update_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.update(
                db_session,
                str(uuid.uuid4()),
                DocumentRetentionUpdate(disposition_status="eligible"),
            )
        assert exc.value.status_code == 404

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        DocumentRetentions.delete(db_session, str(retention.id))
        db_session.refresh(retention)
        assert retention.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_dispose(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        disposed = DocumentRetentions.dispose(
            db_session, str(retention.id), str(person.id)
        )
        assert disposed.disposition_status == DispositionStatus.completed
        assert disposed.disposed_at is not None
        assert disposed.disposed_by == person.id

    def test_dispose_already_completed(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        retention.disposition_status = DispositionStatus.completed
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.dispose(db_session, str(retention.id), str(person.id))
        assert exc.value.status_code == 400
        assert "Retention already disposed" in exc.value.detail

    def test_dispose_invalid_disposer(self, db_session):
        person = _make_person(db_session)
        retention = _make_retention(db_session, person)
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.dispose(db_session, str(retention.id), str(uuid.uuid4()))
        assert exc.value.status_code == 404
        assert "Disposer not found" in exc.value.detail

    def test_dispose_not_found(self, db_session):
        person = _make_person(db_session)
        with pytest.raises(HTTPException) as exc:
            DocumentRetentions.dispose(db_session, str(uuid.uuid4()), str(person.id))
        assert exc.value.status_code == 404
