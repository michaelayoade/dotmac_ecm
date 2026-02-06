from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# WorkflowDefinition
# ---------------------------------------------------------------------------


class WorkflowDefinitionBase(BaseModel):
    name: str
    description: str | None = None
    states: dict
    is_active: bool = True


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    states: dict | None = None
    is_active: bool | None = None


class WorkflowDefinitionRead(WorkflowDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# WorkflowInstance
# ---------------------------------------------------------------------------


class WorkflowInstanceBase(BaseModel):
    definition_id: UUID
    document_id: UUID
    current_state: str
    status: str = "active"
    started_by: UUID
    is_active: bool = True
    metadata_: dict | None = None


class WorkflowInstanceCreate(WorkflowInstanceBase):
    pass


class WorkflowInstanceUpdate(BaseModel):
    current_state: str | None = None
    status: str | None = None
    is_active: bool | None = None
    metadata_: dict | None = None


class WorkflowInstanceRead(WorkflowInstanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# WorkflowTask
# ---------------------------------------------------------------------------


class WorkflowTaskBase(BaseModel):
    instance_id: UUID
    task_type: str
    assignee_id: UUID
    from_state: str
    to_state: str
    due_at: datetime | None = None


class WorkflowTaskCreate(WorkflowTaskBase):
    pass


class WorkflowTaskUpdate(BaseModel):
    status: str | None = None
    decision_comment: str | None = None
    decided_at: datetime | None = None
    assignee_id: UUID | None = None
    due_at: datetime | None = None
    is_active: bool | None = None


class WorkflowTaskRead(WorkflowTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    decision_comment: str | None = None
    decided_at: datetime | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# WorkflowTask Complete request
# ---------------------------------------------------------------------------


class WorkflowTaskCompleteRequest(BaseModel):
    status: str
    decision_comment: str | None = None
