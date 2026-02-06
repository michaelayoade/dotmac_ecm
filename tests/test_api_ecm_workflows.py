import uuid

from app.models.ecm import (
    ClassificationLevel,
    Document,
    DocumentStatus,
    Folder,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
    WorkflowTaskType,
)
from app.models.person import Person


def _create_person(db_session):
    p = Person(
        first_name="API",
        last_name="WF",
        email=f"api-wf-{uuid.uuid4().hex[:8]}@test.com",
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


def _create_definition(db_session):
    defn = WorkflowDefinition(
        name=f"wf_{uuid.uuid4().hex[:8]}",
        description="Test workflow",
        states={"draft": {"transitions": [{"to": "review"}]}},
    )
    db_session.add(defn)
    db_session.commit()
    db_session.refresh(defn)
    return defn


def _create_instance(db_session, person):
    defn = _create_definition(db_session)
    doc = _create_document(db_session, person)
    instance = WorkflowInstance(
        definition_id=defn.id,
        document_id=doc.id,
        current_state="draft",
        status=WorkflowInstanceStatus.active,
        started_by=person.id,
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


def _create_task(db_session, person):
    instance = _create_instance(db_session, person)
    task = WorkflowTask(
        instance_id=instance.id,
        task_type=WorkflowTaskType.approval,
        assignee_id=person.id,
        from_state="draft",
        to_state="review",
        status=WorkflowTaskStatus.pending,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestWorkflowDefinitionEndpoints:
    def test_create(self, client, auth_headers, db_session):
        resp = client.post(
            "/ecm/workflow-definitions",
            json={
                "name": f"wf_{uuid.uuid4().hex[:8]}",
                "description": "Test",
                "states": {"draft": {"transitions": []}},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert "id" in data

    def test_get(self, client, auth_headers, db_session):
        defn = _create_definition(db_session)
        resp = client.get(
            f"/ecm/workflow-definitions/{defn.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(defn.id)

    def test_get_not_found(self, client, auth_headers):
        resp = client.get(
            f"/ecm/workflow-definitions/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, db_session):
        _create_definition(db_session)
        resp = client.get("/ecm/workflow-definitions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 1

    def test_update(self, client, auth_headers, db_session):
        defn = _create_definition(db_session)
        resp = client.patch(
            f"/ecm/workflow-definitions/{defn.id}",
            json={"description": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    def test_delete(self, client, auth_headers, db_session):
        defn = _create_definition(db_session)
        resp = client.delete(
            f"/ecm/workflow-definitions/{defn.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestWorkflowInstanceEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        defn = _create_definition(db_session)
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/workflow-instances",
            json={
                "definition_id": str(defn.id),
                "document_id": str(doc.id),
                "current_state": "draft",
                "status": "active",
                "started_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["definition_id"] == str(defn.id)
        assert data["status"] == "active"

    def test_create_invalid_definition(self, client, auth_headers, db_session, person):
        doc = _create_document(db_session, person)
        resp = client.post(
            "/ecm/workflow-instances",
            json={
                "definition_id": str(uuid.uuid4()),
                "document_id": str(doc.id),
                "current_state": "draft",
                "status": "active",
                "started_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        instance = _create_instance(db_session, person)
        resp = client.get(
            f"/ecm/workflow-instances/{instance.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(instance.id)

    def test_list(self, client, auth_headers, db_session, person):
        _create_instance(db_session, person)
        resp = client.get("/ecm/workflow-instances", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_filter_status(self, client, auth_headers, db_session, person):
        _create_instance(db_session, person)
        resp = client.get(
            "/ecm/workflow-instances?status=active",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_update(self, client, auth_headers, db_session, person):
        instance = _create_instance(db_session, person)
        resp = client.patch(
            f"/ecm/workflow-instances/{instance.id}",
            json={"current_state": "review"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_state"] == "review"

    def test_delete(self, client, auth_headers, db_session, person):
        instance = _create_instance(db_session, person)
        resp = client.delete(
            f"/ecm/workflow-instances/{instance.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestWorkflowTaskEndpoints:
    def test_create(self, client, auth_headers, db_session, person):
        instance = _create_instance(db_session, person)
        resp = client.post(
            "/ecm/workflow-tasks",
            json={
                "instance_id": str(instance.id),
                "task_type": "approval",
                "assignee_id": str(person.id),
                "from_state": "draft",
                "to_state": "review",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_type"] == "approval"
        assert data["status"] == "pending"

    def test_create_invalid_instance(self, client, auth_headers, db_session, person):
        resp = client.post(
            "/ecm/workflow-tasks",
            json={
                "instance_id": str(uuid.uuid4()),
                "task_type": "approval",
                "assignee_id": str(person.id),
                "from_state": "draft",
                "to_state": "review",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.get(
            f"/ecm/workflow-tasks/{task.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    def test_list(self, client, auth_headers, db_session, person):
        _create_task(db_session, person)
        resp = client.get("/ecm/workflow-tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_update(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.patch(
            f"/ecm/workflow-tasks/{task.id}",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_delete(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.delete(
            f"/ecm/workflow-tasks/{task.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_complete_approved(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.post(
            f"/ecm/workflow-tasks/{task.id}/complete",
            json={"status": "approved", "decision_comment": "Looks good"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["decision_comment"] == "Looks good"
        assert data["decided_at"] is not None

    def test_complete_rejected(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.post(
            f"/ecm/workflow-tasks/{task.id}/complete",
            json={"status": "rejected", "decision_comment": "Needs changes"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_complete_invalid_status(self, client, auth_headers, db_session, person):
        task = _create_task(db_session, person)
        resp = client.post(
            f"/ecm/workflow-tasks/{task.id}/complete",
            json={"status": "cancelled"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_complete_not_found(self, client, auth_headers):
        resp = client.post(
            f"/ecm/workflow-tasks/{uuid.uuid4()}/complete",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
