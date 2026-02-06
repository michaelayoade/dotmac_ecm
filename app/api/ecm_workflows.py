from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_workflow import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
    WorkflowInstanceCreate,
    WorkflowInstanceRead,
    WorkflowInstanceUpdate,
    WorkflowTaskCompleteRequest,
    WorkflowTaskCreate,
    WorkflowTaskRead,
    WorkflowTaskUpdate,
)
from app.services import ecm_workflow as wf_service

router = APIRouter(prefix="/ecm", tags=["ecm-workflows"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# WorkflowDefinition CRUD
# ------------------------------------------------------------------


@router.post(
    "/workflow-definitions",
    response_model=WorkflowDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_definition(
    payload: WorkflowDefinitionCreate, db: Session = Depends(get_db)
):
    return wf_service.workflow_definitions.create(db, payload)


@router.get(
    "/workflow-definitions/{definition_id}",
    response_model=WorkflowDefinitionRead,
)
def get_workflow_definition(definition_id: str, db: Session = Depends(get_db)):
    return wf_service.workflow_definitions.get(db, definition_id)


@router.get(
    "/workflow-definitions",
    response_model=ListResponse[WorkflowDefinitionRead],
)
def list_workflow_definitions(
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return wf_service.workflow_definitions.list_response(
        db, is_active, order_by, order_dir, limit, offset
    )


@router.patch(
    "/workflow-definitions/{definition_id}",
    response_model=WorkflowDefinitionRead,
)
def update_workflow_definition(
    definition_id: str,
    payload: WorkflowDefinitionUpdate,
    db: Session = Depends(get_db),
):
    return wf_service.workflow_definitions.update(db, definition_id, payload)


@router.delete(
    "/workflow-definitions/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow_definition(definition_id: str, db: Session = Depends(get_db)):
    wf_service.workflow_definitions.delete(db, definition_id)


# ------------------------------------------------------------------
# WorkflowInstance CRUD
# ------------------------------------------------------------------


@router.post(
    "/workflow-instances",
    response_model=WorkflowInstanceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_instance(
    payload: WorkflowInstanceCreate, db: Session = Depends(get_db)
):
    return wf_service.workflow_instances.create(db, payload)


@router.get(
    "/workflow-instances/{instance_id}",
    response_model=WorkflowInstanceRead,
)
def get_workflow_instance(instance_id: str, db: Session = Depends(get_db)):
    return wf_service.workflow_instances.get(db, instance_id)


@router.get(
    "/workflow-instances",
    response_model=ListResponse[WorkflowInstanceRead],
)
def list_workflow_instances(
    definition_id: str | None = None,
    document_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    started_by: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return wf_service.workflow_instances.list_response(
        db,
        definition_id,
        document_id,
        status_filter,
        started_by,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/workflow-instances/{instance_id}",
    response_model=WorkflowInstanceRead,
)
def update_workflow_instance(
    instance_id: str,
    payload: WorkflowInstanceUpdate,
    db: Session = Depends(get_db),
):
    return wf_service.workflow_instances.update(db, instance_id, payload)


@router.delete(
    "/workflow-instances/{instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow_instance(instance_id: str, db: Session = Depends(get_db)):
    wf_service.workflow_instances.delete(db, instance_id)


# ------------------------------------------------------------------
# WorkflowTask CRUD + Complete
# ------------------------------------------------------------------


@router.post(
    "/workflow-tasks",
    response_model=WorkflowTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_task(payload: WorkflowTaskCreate, db: Session = Depends(get_db)):
    return wf_service.workflow_tasks.create(db, payload)


@router.get(
    "/workflow-tasks/{task_id}",
    response_model=WorkflowTaskRead,
)
def get_workflow_task(task_id: str, db: Session = Depends(get_db)):
    return wf_service.workflow_tasks.get(db, task_id)


@router.get(
    "/workflow-tasks",
    response_model=ListResponse[WorkflowTaskRead],
)
def list_workflow_tasks(
    instance_id: str | None = None,
    assignee_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return wf_service.workflow_tasks.list_response(
        db,
        instance_id,
        assignee_id,
        status_filter,
        task_type,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/workflow-tasks/{task_id}",
    response_model=WorkflowTaskRead,
)
def update_workflow_task(
    task_id: str,
    payload: WorkflowTaskUpdate,
    db: Session = Depends(get_db),
):
    return wf_service.workflow_tasks.update(db, task_id, payload)


@router.delete(
    "/workflow-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow_task(task_id: str, db: Session = Depends(get_db)):
    wf_service.workflow_tasks.delete(db, task_id)


@router.post(
    "/workflow-tasks/{task_id}/complete",
    response_model=WorkflowTaskRead,
)
def complete_workflow_task(
    task_id: str,
    payload: WorkflowTaskCompleteRequest,
    db: Session = Depends(get_db),
):
    return wf_service.workflow_tasks.complete(
        db, task_id, payload.status, payload.decision_comment
    )
