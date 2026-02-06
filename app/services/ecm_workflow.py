import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import (
    Document,
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
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


def _validate_instance_status(status: str) -> None:
    try:
        WorkflowInstanceStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}",
        )


def _validate_task_type(task_type: str) -> None:
    try:
        WorkflowTaskType(task_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_type: {task_type}",
        )


def _validate_task_status(status: str) -> None:
    try:
        WorkflowTaskStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}",
        )


# ---------------------------------------------------------------------------
# WorkflowDefinitions
# ---------------------------------------------------------------------------


class WorkflowDefinitions(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: WorkflowDefinitionCreate) -> WorkflowDefinition:
        data = payload.model_dump()
        defn = WorkflowDefinition(**data)
        db.add(defn)
        db.commit()
        db.refresh(defn)
        logger.info("Created workflow definition %s", defn.id)
        return defn

    @staticmethod
    def get(db: Session, definition_id: str) -> WorkflowDefinition:
        defn = db.get(WorkflowDefinition, coerce_uuid(definition_id))
        if not defn:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        return defn

    @staticmethod
    def list(
        db: Session,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[WorkflowDefinition]:
        query = db.query(WorkflowDefinition)
        if is_active is None:
            query = query.filter(WorkflowDefinition.is_active.is_(True))
        else:
            query = query.filter(WorkflowDefinition.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {
                "name": WorkflowDefinition.name,
                "created_at": WorkflowDefinition.created_at,
            },
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session,
        definition_id: str,
        payload: WorkflowDefinitionUpdate,
    ) -> WorkflowDefinition:
        defn = db.get(WorkflowDefinition, coerce_uuid(definition_id))
        if not defn:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(defn, key, value)
        db.commit()
        db.refresh(defn)
        logger.info("Updated workflow definition %s", defn.id)
        return defn

    @staticmethod
    def delete(db: Session, definition_id: str) -> None:
        defn = db.get(WorkflowDefinition, coerce_uuid(definition_id))
        if not defn:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        defn.is_active = False
        db.commit()
        logger.info("Soft-deleted workflow definition %s", definition_id)


# ---------------------------------------------------------------------------
# WorkflowInstances
# ---------------------------------------------------------------------------


class WorkflowInstances(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: WorkflowInstanceCreate) -> WorkflowInstance:
        defn = db.get(WorkflowDefinition, coerce_uuid(payload.definition_id))
        if not defn:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(Person, coerce_uuid(payload.started_by)):
            raise HTTPException(status_code=404, detail="Started-by person not found")
        _validate_instance_status(payload.status)

        data = payload.model_dump()
        data["status"] = WorkflowInstanceStatus(data["status"])
        instance = WorkflowInstance(**data)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        logger.info("Created workflow instance %s", instance.id)
        return instance

    @staticmethod
    def get(db: Session, instance_id: str) -> WorkflowInstance:
        instance = db.get(WorkflowInstance, coerce_uuid(instance_id))
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        return instance

    @staticmethod
    def list(
        db: Session,
        definition_id: str | None,
        document_id: str | None,
        status: str | None,
        started_by: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[WorkflowInstance]:
        query = db.query(WorkflowInstance)
        if definition_id is not None:
            query = query.filter(
                WorkflowInstance.definition_id == coerce_uuid(definition_id)
            )
        if document_id is not None:
            query = query.filter(
                WorkflowInstance.document_id == coerce_uuid(document_id)
            )
        if status is not None:
            query = query.filter(
                WorkflowInstance.status == WorkflowInstanceStatus(status)
            )
        if started_by is not None:
            query = query.filter(WorkflowInstance.started_by == coerce_uuid(started_by))
        if is_active is None:
            query = query.filter(WorkflowInstance.is_active.is_(True))
        else:
            query = query.filter(WorkflowInstance.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": WorkflowInstance.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session,
        instance_id: str,
        payload: WorkflowInstanceUpdate,
    ) -> WorkflowInstance:
        instance = db.get(WorkflowInstance, coerce_uuid(instance_id))
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        data = payload.model_dump(exclude_unset=True)
        if "status" in data:
            _validate_instance_status(data["status"])
            data["status"] = WorkflowInstanceStatus(data["status"])
        for key, value in data.items():
            setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        logger.info("Updated workflow instance %s", instance.id)
        return instance

    @staticmethod
    def delete(db: Session, instance_id: str) -> None:
        instance = db.get(WorkflowInstance, coerce_uuid(instance_id))
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        instance.is_active = False
        db.commit()
        logger.info("Soft-deleted workflow instance %s", instance_id)


# ---------------------------------------------------------------------------
# WorkflowTasks
# ---------------------------------------------------------------------------


class WorkflowTasks(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: WorkflowTaskCreate) -> WorkflowTask:
        if not db.get(WorkflowInstance, coerce_uuid(payload.instance_id)):
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        if not db.get(Person, coerce_uuid(payload.assignee_id)):
            raise HTTPException(status_code=404, detail="Assignee not found")
        _validate_task_type(payload.task_type)

        data = payload.model_dump()
        data["task_type"] = WorkflowTaskType(data["task_type"])
        task = WorkflowTask(**data)
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info("Created workflow task %s", task.id)
        return task

    @staticmethod
    def get(db: Session, task_id: str) -> WorkflowTask:
        task = db.get(WorkflowTask, coerce_uuid(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Workflow task not found")
        return task

    @staticmethod
    def list(
        db: Session,
        instance_id: str | None,
        assignee_id: str | None,
        status: str | None,
        task_type: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[WorkflowTask]:
        query = db.query(WorkflowTask)
        if instance_id is not None:
            query = query.filter(WorkflowTask.instance_id == coerce_uuid(instance_id))
        if assignee_id is not None:
            query = query.filter(WorkflowTask.assignee_id == coerce_uuid(assignee_id))
        if status is not None:
            query = query.filter(WorkflowTask.status == WorkflowTaskStatus(status))
        if task_type is not None:
            query = query.filter(WorkflowTask.task_type == WorkflowTaskType(task_type))
        if is_active is None:
            query = query.filter(WorkflowTask.is_active.is_(True))
        else:
            query = query.filter(WorkflowTask.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": WorkflowTask.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(db: Session, task_id: str, payload: WorkflowTaskUpdate) -> WorkflowTask:
        task = db.get(WorkflowTask, coerce_uuid(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Workflow task not found")
        data = payload.model_dump(exclude_unset=True)
        if "status" in data:
            _validate_task_status(data["status"])
            data["status"] = WorkflowTaskStatus(data["status"])
        for key, value in data.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        logger.info("Updated workflow task %s", task.id)
        return task

    @staticmethod
    def delete(db: Session, task_id: str) -> None:
        task = db.get(WorkflowTask, coerce_uuid(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Workflow task not found")
        task.is_active = False
        db.commit()
        logger.info("Soft-deleted workflow task %s", task_id)

    @staticmethod
    def complete(
        db: Session,
        task_id: str,
        status: str,
        decision_comment: str | None = None,
    ) -> WorkflowTask:
        task = db.get(WorkflowTask, coerce_uuid(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Workflow task not found")
        if task.status != WorkflowTaskStatus.pending:
            raise HTTPException(status_code=400, detail="Task is not pending")
        if status not in ("approved", "rejected"):
            raise HTTPException(
                status_code=400,
                detail="Status must be approved or rejected",
            )
        task.status = WorkflowTaskStatus(status)
        task.decision_comment = decision_comment
        task.decided_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)
        logger.info("Completed workflow task %s with status %s", task.id, status)
        return task


workflow_definitions = WorkflowDefinitions()
workflow_instances = WorkflowInstances()
workflow_tasks = WorkflowTasks()
