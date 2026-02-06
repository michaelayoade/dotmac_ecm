from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_acl import (
    DocumentACLCreate,
    DocumentACLRead,
    DocumentACLUpdate,
    FolderACLCreate,
    FolderACLRead,
    FolderACLUpdate,
)
from app.services import ecm_acl as acl_service

router = APIRouter(prefix="/ecm", tags=["ecm-acl"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# DocumentACL CRUD
# ------------------------------------------------------------------


@router.post(
    "/document-acls",
    response_model=DocumentACLRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_acl(payload: DocumentACLCreate, db: Session = Depends(get_db)):
    return acl_service.document_acls.create(db, payload)


@router.get("/document-acls/{acl_id}", response_model=DocumentACLRead)
def get_document_acl(acl_id: str, db: Session = Depends(get_db)):
    return acl_service.document_acls.get(db, acl_id)


@router.get("/document-acls", response_model=ListResponse[DocumentACLRead])
def list_document_acls(
    document_id: str | None = None,
    principal_type: str | None = None,
    principal_id: str | None = None,
    permission: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return acl_service.document_acls.list_response(
        db,
        document_id,
        principal_type,
        principal_id,
        permission,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch("/document-acls/{acl_id}", response_model=DocumentACLRead)
def update_document_acl(
    acl_id: str, payload: DocumentACLUpdate, db: Session = Depends(get_db)
):
    return acl_service.document_acls.update(db, acl_id, payload)


@router.delete("/document-acls/{acl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_acl(acl_id: str, db: Session = Depends(get_db)):
    acl_service.document_acls.delete(db, acl_id)


# ------------------------------------------------------------------
# FolderACL CRUD
# ------------------------------------------------------------------


@router.post(
    "/folder-acls",
    response_model=FolderACLRead,
    status_code=status.HTTP_201_CREATED,
)
def create_folder_acl(payload: FolderACLCreate, db: Session = Depends(get_db)):
    return acl_service.folder_acls.create(db, payload)


@router.get("/folder-acls/{acl_id}", response_model=FolderACLRead)
def get_folder_acl(acl_id: str, db: Session = Depends(get_db)):
    return acl_service.folder_acls.get(db, acl_id)


@router.get("/folder-acls", response_model=ListResponse[FolderACLRead])
def list_folder_acls(
    folder_id: str | None = None,
    principal_type: str | None = None,
    principal_id: str | None = None,
    permission: str | None = None,
    is_inherited: bool | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return acl_service.folder_acls.list_response(
        db,
        folder_id,
        principal_type,
        principal_id,
        permission,
        is_inherited,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch("/folder-acls/{acl_id}", response_model=FolderACLRead)
def update_folder_acl(
    acl_id: str, payload: FolderACLUpdate, db: Session = Depends(get_db)
):
    return acl_service.folder_acls.update(db, acl_id, payload)


@router.delete("/folder-acls/{acl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder_acl(acl_id: str, db: Session = Depends(get_db)):
    acl_service.folder_acls.delete(db, acl_id)
