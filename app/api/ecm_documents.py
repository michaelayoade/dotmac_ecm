from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    DocumentVersionCreate,
    DocumentVersionRead,
    DownloadURLResponse,
    UploadURLRequest,
    UploadURLResponse,
)
from app.services import ecm_document as doc_service
from app.services.ecm_storage import storage

router = APIRouter(prefix="/ecm/documents", tags=["ecm-documents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# Document CRUD
# ------------------------------------------------------------------


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    return doc_service.documents.create(db, payload)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    return doc_service.documents.get(db, document_id)


@router.get("", response_model=ListResponse[DocumentRead])
def list_documents(
    folder_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    classification: str | None = None,
    content_type_id: str | None = None,
    created_by: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return doc_service.documents.list_response(
        db,
        folder_id,
        status_filter,
        classification,
        content_type_id,
        created_by,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: str, payload: DocumentUpdate, db: Session = Depends(get_db)
):
    return doc_service.documents.update(db, document_id, payload)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc_service.documents.delete(db, document_id)


# ------------------------------------------------------------------
# Version sub-endpoints
# ------------------------------------------------------------------


@router.post(
    "/{document_id}/versions",
    response_model=DocumentVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    document_id: str,
    payload: DocumentVersionCreate,
    db: Session = Depends(get_db),
):
    return doc_service.documents.create_version(db, document_id, payload)


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionRead)
def get_version(document_id: str, version_id: str, db: Session = Depends(get_db)):
    return doc_service.documents.get_version(db, document_id, version_id)


@router.get(
    "/{document_id}/versions",
    response_model=ListResponse[DocumentVersionRead],
)
def list_versions(
    document_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items = doc_service.documents.list_versions(db, document_id, limit, offset)
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}


@router.delete(
    "/{document_id}/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_version(document_id: str, version_id: str, db: Session = Depends(get_db)):
    doc_service.documents.delete_version(db, document_id, version_id)


# ------------------------------------------------------------------
# Storage presigned-URL endpoints
# ------------------------------------------------------------------


@router.post("/{document_id}/upload-url", response_model=UploadURLResponse)
def generate_upload_url(
    document_id: str,
    payload: UploadURLRequest,
    db: Session = Depends(get_db),
):
    doc_service.documents.get(db, document_id)
    storage_key = storage.generate_storage_key(document_id, payload.file_name)
    upload_url = storage.generate_upload_url(storage_key, payload.mime_type)
    return UploadURLResponse(upload_url=upload_url, storage_key=storage_key)


@router.get(
    "/{document_id}/versions/{version_id}/download-url",
    response_model=DownloadURLResponse,
)
def generate_download_url(
    document_id: str, version_id: str, db: Session = Depends(get_db)
):
    version = doc_service.documents.get_version(db, document_id, version_id)
    download_url = storage.generate_download_url(version.storage_key)
    return DownloadURLResponse(download_url=download_url)
