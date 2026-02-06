import uuid

import pytest
from fastapi import HTTPException

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
from app.schemas.ecm_workflow import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowInstanceCreate,
    WorkflowInstanceUpdate,
    WorkflowTaskCreate,
    WorkflowTaskUpdate,
)
from app.services.ecm_workflow import (
    WorkflowDefinitions,
    WorkflowInstances,
    WorkflowTasks,
)


def _make_person(db_session):
    p = Person(
        first_name="WF",
        last_name="Tester",
        email=f"wf-{uuid.uuid4().hex[:8]}@test.com",
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


def _make_definition(db_session):
    defn = WorkflowDefinition(
        name=f"wf_{uuid.uuid4().hex[:8]}",
        description="Test workflow",
        states={
            "draft": {"transitions": [{"to": "review"}]},
            "review": {"transitions": [{"to": "approved"}, {"to": "draft"}]},
            "approved": {"transitions": []},
        },
    )
    db_session.add(defn)
    db_session.commit()
    db_session.refresh(defn)
    return defn


def _make_instance(db_session, person, defn=None, doc=None):
    if defn is None:
        defn = _make_definition(db_session)
    if doc is None:
        doc = _make_document(db_session, person)
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


def _make_task(db_session, person, instance=None):
    if instance is None:
        instance = _make_instance(db_session, person)
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


class TestWorkflowDefinitions:
    def test_create(self, db_session):
        payload = WorkflowDefinitionCreate(
            name=f"wf_{uuid.uuid4().hex[:8]}",
            description="Test workflow",
            states={"draft": {"transitions": [{"to": "review"}]}},
        )
        defn = WorkflowDefinitions.create(db_session, payload)
        assert defn.name == payload.name
        assert defn.states == payload.states
        assert defn.is_active is True

    def test_get(self, db_session):
        defn = _make_definition(db_session)
        found = WorkflowDefinitions.get(db_session, str(defn.id))
        assert found.id == defn.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowDefinitions.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_default_active(self, db_session):
        defn = _make_definition(db_session)
        results = WorkflowDefinitions.list(
            db_session,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert defn.id in ids

    def test_list_filter_inactive(self, db_session):
        defn = _make_definition(db_session)
        defn.is_active = False
        db_session.commit()
        results = WorkflowDefinitions.list(
            db_session,
            is_active=False,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        ids = [r.id for r in results]
        assert defn.id in ids

    def test_list_order_by_name(self, db_session):
        _make_definition(db_session)
        results = WorkflowDefinitions.list(
            db_session,
            is_active=None,
            order_by="name",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        defn = _make_definition(db_session)
        updated = WorkflowDefinitions.update(
            db_session,
            str(defn.id),
            WorkflowDefinitionUpdate(description="Updated description"),
        )
        assert updated.description == "Updated description"

    def test_update_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowDefinitions.update(
                db_session,
                str(uuid.uuid4()),
                WorkflowDefinitionUpdate(description="x"),
            )
        assert exc.value.status_code == 404

    def test_soft_delete(self, db_session):
        defn = _make_definition(db_session)
        WorkflowDefinitions.delete(db_session, str(defn.id))
        db_session.refresh(defn)
        assert defn.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowDefinitions.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestWorkflowInstances:
    def test_create(self, db_session):
        person = _make_person(db_session)
        defn = _make_definition(db_session)
        doc = _make_document(db_session, person)
        payload = WorkflowInstanceCreate(
            definition_id=defn.id,
            document_id=doc.id,
            current_state="draft",
            status="active",
            started_by=person.id,
        )
        instance = WorkflowInstances.create(db_session, payload)
        assert instance.definition_id == defn.id
        assert instance.document_id == doc.id
        assert instance.current_state == "draft"
        assert instance.status == WorkflowInstanceStatus.active

    def test_create_invalid_definition(self, db_session):
        person = _make_person(db_session)
        doc = _make_document(db_session, person)
        payload = WorkflowInstanceCreate(
            definition_id=uuid.uuid4(),
            document_id=doc.id,
            current_state="draft",
            status="active",
            started_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Workflow definition not found" in exc.value.detail

    def test_create_invalid_document(self, db_session):
        person = _make_person(db_session)
        defn = _make_definition(db_session)
        payload = WorkflowInstanceCreate(
            definition_id=defn.id,
            document_id=uuid.uuid4(),
            current_state="draft",
            status="active",
            started_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Document not found" in exc.value.detail

    def test_create_invalid_started_by(self, db_session):
        person = _make_person(db_session)
        defn = _make_definition(db_session)
        doc = _make_document(db_session, person)
        payload = WorkflowInstanceCreate(
            definition_id=defn.id,
            document_id=doc.id,
            current_state="draft",
            status="active",
            started_by=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Started-by person not found" in exc.value.detail

    def test_create_invalid_status(self, db_session):
        person = _make_person(db_session)
        defn = _make_definition(db_session)
        doc = _make_document(db_session, person)
        payload = WorkflowInstanceCreate(
            definition_id=defn.id,
            document_id=doc.id,
            current_state="draft",
            status="invalid",
            started_by=person.id,
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_get(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        found = WorkflowInstances.get(db_session, str(instance.id))
        assert found.id == instance.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_definition(self, db_session):
        person = _make_person(db_session)
        defn = _make_definition(db_session)
        doc = _make_document(db_session, person)
        _make_instance(db_session, person, defn=defn, doc=doc)
        results = WorkflowInstances.list(
            db_session,
            definition_id=str(defn.id),
            document_id=None,
            status=None,
            started_by=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.definition_id == defn.id for r in results)

    def test_list_filter_by_status(self, db_session):
        person = _make_person(db_session)
        _make_instance(db_session, person)
        results = WorkflowInstances.list(
            db_session,
            definition_id=None,
            document_id=None,
            status="active",
            started_by=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        updated = WorkflowInstances.update(
            db_session,
            str(instance.id),
            WorkflowInstanceUpdate(current_state="review", status="completed"),
        )
        assert updated.current_state == "review"
        assert updated.status == WorkflowInstanceStatus.completed

    def test_update_invalid_status(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.update(
                db_session,
                str(instance.id),
                WorkflowInstanceUpdate(status="invalid"),
            )
        assert exc.value.status_code == 400

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        WorkflowInstances.delete(db_session, str(instance.id))
        db_session.refresh(instance)
        assert instance.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowInstances.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestWorkflowTasks:
    def test_create(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        payload = WorkflowTaskCreate(
            instance_id=instance.id,
            task_type="approval",
            assignee_id=person.id,
            from_state="draft",
            to_state="review",
        )
        task = WorkflowTasks.create(db_session, payload)
        assert task.instance_id == instance.id
        assert task.task_type == WorkflowTaskType.approval
        assert task.status == WorkflowTaskStatus.pending

    def test_create_invalid_instance(self, db_session):
        person = _make_person(db_session)
        payload = WorkflowTaskCreate(
            instance_id=uuid.uuid4(),
            task_type="approval",
            assignee_id=person.id,
            from_state="draft",
            to_state="review",
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Workflow instance not found" in exc.value.detail

    def test_create_invalid_assignee(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        payload = WorkflowTaskCreate(
            instance_id=instance.id,
            task_type="approval",
            assignee_id=uuid.uuid4(),
            from_state="draft",
            to_state="review",
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Assignee not found" in exc.value.detail

    def test_create_invalid_task_type(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        payload = WorkflowTaskCreate(
            instance_id=instance.id,
            task_type="invalid",
            assignee_id=person.id,
            from_state="draft",
            to_state="review",
        )
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.create(db_session, payload)
        assert exc.value.status_code == 400

    def test_get(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        found = WorkflowTasks.get(db_session, str(task.id))
        assert found.id == task.id

    def test_get_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list_filter_by_instance(self, db_session):
        person = _make_person(db_session)
        instance = _make_instance(db_session, person)
        _make_task(db_session, person, instance=instance)
        results = WorkflowTasks.list(
            db_session,
            instance_id=str(instance.id),
            assignee_id=None,
            status=None,
            task_type=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.instance_id == instance.id for r in results)

    def test_list_filter_by_assignee(self, db_session):
        person = _make_person(db_session)
        _make_task(db_session, person)
        results = WorkflowTasks.list(
            db_session,
            instance_id=None,
            assignee_id=str(person.id),
            status=None,
            task_type=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1
        assert all(r.assignee_id == person.id for r in results)

    def test_list_filter_by_status(self, db_session):
        person = _make_person(db_session)
        _make_task(db_session, person)
        results = WorkflowTasks.list(
            db_session,
            instance_id=None,
            assignee_id=None,
            status="pending",
            task_type=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_list_filter_by_task_type(self, db_session):
        person = _make_person(db_session)
        _make_task(db_session, person)
        results = WorkflowTasks.list(
            db_session,
            instance_id=None,
            assignee_id=None,
            status=None,
            task_type="approval",
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=50,
            offset=0,
        )
        assert len(results) >= 1

    def test_update(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        updated = WorkflowTasks.update(
            db_session,
            str(task.id),
            WorkflowTaskUpdate(status="approved"),
        )
        assert updated.status == WorkflowTaskStatus.approved

    def test_update_invalid_status(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.update(
                db_session,
                str(task.id),
                WorkflowTaskUpdate(status="invalid"),
            )
        assert exc.value.status_code == 400

    def test_soft_delete(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        WorkflowTasks.delete(db_session, str(task.id))
        db_session.refresh(task)
        assert task.is_active is False

    def test_delete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_complete_approved(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        completed = WorkflowTasks.complete(
            db_session, str(task.id), "approved", "Looks good"
        )
        assert completed.status == WorkflowTaskStatus.approved
        assert completed.decision_comment == "Looks good"
        assert completed.decided_at is not None

    def test_complete_rejected(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        completed = WorkflowTasks.complete(
            db_session, str(task.id), "rejected", "Needs changes"
        )
        assert completed.status == WorkflowTaskStatus.rejected
        assert completed.decision_comment == "Needs changes"

    def test_complete_not_pending(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        task.status = WorkflowTaskStatus.approved
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.complete(db_session, str(task.id), "approved")
        assert exc.value.status_code == 400
        assert "Task is not pending" in exc.value.detail

    def test_complete_invalid_status(self, db_session):
        person = _make_person(db_session)
        task = _make_task(db_session, person)
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.complete(db_session, str(task.id), "cancelled")
        assert exc.value.status_code == 400
        assert "Status must be approved or rejected" in exc.value.detail

    def test_complete_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            WorkflowTasks.complete(db_session, str(uuid.uuid4()), "approved")
        assert exc.value.status_code == 404
