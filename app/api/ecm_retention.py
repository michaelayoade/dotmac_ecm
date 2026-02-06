from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_retention import (
    DisposeRequest,
    DocumentRetentionCreate,
    DocumentRetentionRead,
    DocumentRetentionUpdate,
    RetentionPolicyCreate,
    RetentionPolicyRead,
    RetentionPolicyUpdate,
)
from app.services import ecm_retention as ret_service

router = APIRouter(prefix="/ecm", tags=["ecm-retention"])


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ------------------------------------------------------------------
# RetentionPolicy CRUD
# ------------------------------------------------------------------


@router.post(
    "/retention-policies",
    response_model=RetentionPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_retention_policy(
    payload: RetentionPolicyCreate, db: Session = Depends(get_db)
) -> RetentionPolicyRead:
    return ret_service.retention_policies.create(db, payload)


@router.get(
    "/retention-policies/{policy_id}",
    response_model=RetentionPolicyRead,
)
def get_retention_policy(
    policy_id: str, db: Session = Depends(get_db)
) -> RetentionPolicyRead:
    return ret_service.retention_policies.get(db, policy_id)


@router.get(
    "/retention-policies",
    response_model=ListResponse[RetentionPolicyRead],
)
def list_retention_policies(
    disposition_action: str | None = None,
    content_type_id: str | None = None,
    category_id: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return ret_service.retention_policies.list_response(
        db,
        disposition_action,
        content_type_id,
        category_id,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/retention-policies/{policy_id}",
    response_model=RetentionPolicyRead,
)
def update_retention_policy(
    policy_id: str,
    payload: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
) -> RetentionPolicyRead:
    return ret_service.retention_policies.update(db, policy_id, payload)


@router.delete(
    "/retention-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_retention_policy(policy_id: str, db: Session = Depends(get_db)) -> None:
    ret_service.retention_policies.delete(db, policy_id)


# ------------------------------------------------------------------
# DocumentRetention CRUD + Dispose
# ------------------------------------------------------------------


@router.post(
    "/document-retentions",
    response_model=DocumentRetentionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_retention(
    payload: DocumentRetentionCreate, db: Session = Depends(get_db)
) -> DocumentRetentionRead:
    return ret_service.document_retentions.create(db, payload)


@router.get(
    "/document-retentions/{retention_id}",
    response_model=DocumentRetentionRead,
)
def get_document_retention(
    retention_id: str, db: Session = Depends(get_db)
) -> DocumentRetentionRead:
    return ret_service.document_retentions.get(db, retention_id)


@router.get(
    "/document-retentions",
    response_model=ListResponse[DocumentRetentionRead],
)
def list_document_retentions(
    document_id: str | None = None,
    policy_id: str | None = None,
    disposition_status: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return ret_service.document_retentions.list_response(
        db,
        document_id,
        policy_id,
        disposition_status,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/document-retentions/{retention_id}",
    response_model=DocumentRetentionRead,
)
def update_document_retention(
    retention_id: str,
    payload: DocumentRetentionUpdate,
    db: Session = Depends(get_db),
) -> DocumentRetentionRead:
    return ret_service.document_retentions.update(db, retention_id, payload)


@router.delete(
    "/document-retentions/{retention_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_retention(retention_id: str, db: Session = Depends(get_db)) -> None:
    ret_service.document_retentions.delete(db, retention_id)


@router.post(
    "/document-retentions/{retention_id}/dispose",
    response_model=DocumentRetentionRead,
)
def dispose_document_retention(
    retention_id: str,
    payload: DisposeRequest,
    db: Session = Depends(get_db),
) -> DocumentRetentionRead:
    return ret_service.document_retentions.dispose(
        db, retention_id, str(payload.disposed_by)
    )
