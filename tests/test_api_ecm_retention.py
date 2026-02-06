import uuid
from datetime import datetime, timezone

from app.models.ecm import (
    ClassificationLevel,
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentRetention,
    DocumentStatus,
    Folder,
    RetentionPolicy,
)
from app.models.person import Person


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="Ret",
        email=f"api-ret-{uuid.uuid4().hex[:8]}@test.com",
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


def _create_policy(db_session):
    policy = RetentionPolicy(
        name=f"policy_{uuid.uuid4().hex[:8]}",
        description="Test retention policy",
        retention_days=365,
        disposition_action=DispositionAction.archive,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


def _create_retention(db_session, person):
    policy = _create_policy(db_session)
    doc = _create_document(db_session, person)
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


class TestRetentionPolicyEndpoints:
    def test_create(self, client, auth_headers, db_session):
        resp = client.post(
            "/ecm/retention-policies",
            json={
                "name": f"policy_{uuid.uuid4().hex[:8]}",
                "description": "Test",
                "retention_days": 365,
                "disposition_action": "archive",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert "id" in data
        assert data["disposition_action"] == "archive"

    def test_create_invalid_action(self, client, auth_headers):
        resp = client.post(
            "/ecm/retention-policies",
            json={
                "name": f"policy_{uuid.uuid4().hex[:8]}",
                "retention_days": 365,
                "disposition_action": "invalid",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_get(self, client, auth_headers, db_session):
        policy = _create_policy(db_session)
        resp = client.get(
            f"/ecm/retention-policies/{policy.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(policy.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/retention-policies/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session):
        _create_policy(db_session)
        resp = client.get("/ecm/retention-policies", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 1

    def test_list_filter_disposition_action(self, client, auth_headers, db_session):
        _create_policy(db_session)
        resp = client.get(
            "/ecm/retention-policies?disposition_action=archive",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_update(self, client, auth_headers, db_session):
        policy = _create_policy(db_session)
        resp = client.patch(
            f"/ecm/retention-policies/{policy.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    def test_delete(self, client, auth_headers, db_session):
        policy = _create_policy(db_session)
        resp = client.delete(
            f"/ecm/retention-policies/{policy.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestDocumentRetentionEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        policy = _create_policy(db_session)
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/document-retentions",
            json={
                "document_id": str(doc.id),
                "policy_id": str(policy.id),
                "retention_expires_at": "2030-01-01T00:00:00Z",
                "disposition_status": "pending",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] == str(doc.id)
        assert data["disposition_status"] == "pending"

    def test_create_invalid_document(self, client, auth_headers, db_session):
        policy = _create_policy(db_session)
        resp = client.post(
            "/ecm/document-retentions",
            json={
                "document_id": str(uuid.uuid4()),
                "policy_id": str(policy.id),
                "retention_expires_at": "2030-01-01T00:00:00Z",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        retention = _create_retention(db_session, person)
        resp = client.get(
            f"/ecm/document-retentions/{retention.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(retention.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/document-retentions/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session, person):
        _create_retention(db_session, person)
        resp = client.get("/ecm/document-retentions", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_filter_status(self, client, auth_headers, db_session, person):
        _create_retention(db_session, person)
        resp = client.get(
            "/ecm/document-retentions?disposition_status=pending",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_update(self, client, auth_headers, db_session, person):
        retention = _create_retention(db_session, person)
        resp = client.patch(
            f"/ecm/document-retentions/{retention.id}",
            json={"disposition_status": "eligible"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disposition_status"] == "eligible"

    def test_delete(self, client, auth_headers, db_session, person):
        retention = _create_retention(db_session, person)
        resp = client.delete(
            f"/ecm/document-retentions/{retention.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_dispose(self, client, auth_headers, db_session, person):
        retention = _create_retention(db_session, person)
        resp = client.post(
            f"/ecm/document-retentions/{retention.id}/dispose",
            json={"disposed_by": str(person.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["disposition_status"] == "completed"
        assert data["disposed_at"] is not None
        assert data["disposed_by"] == str(person.id)

    def test_dispose_already_completed(self, client, auth_headers, db_session, person):
        retention = _create_retention(db_session, person)
        retention.disposition_status = DispositionStatus.completed
        db_session.commit()
        resp = client.post(
            f"/ecm/document-retentions/{retention.id}/dispose",
            json={"disposed_by": str(person.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_dispose_not_found(self, client, auth_headers, person):
        resp = client.post(
            f"/ecm/document-retentions/{uuid.uuid4()}/dispose",
            json={"disposed_by": str(person.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 404
