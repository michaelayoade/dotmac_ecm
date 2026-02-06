from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_legal_hold import (
    LegalHoldCreate,
    LegalHoldDocumentCreate,
    LegalHoldDocumentRead,
    LegalHoldRead,
    LegalHoldUpdate,
)
from app.services import ecm_legal_hold as lh_service

router = APIRouter(prefix="/ecm", tags=["ecm-legal-holds"])


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
# LegalHold CRUD
# ------------------------------------------------------------------


@router.post(
    "/legal-holds",
    response_model=LegalHoldRead,
    status_code=status.HTTP_201_CREATED,
)
def create_legal_hold(
    payload: LegalHoldCreate, db: Session = Depends(get_db)
) -> LegalHoldRead:
    return lh_service.legal_holds.create(db, payload)


@router.get(
    "/legal-holds/{hold_id}",
    response_model=LegalHoldRead,
)
def get_legal_hold(hold_id: str, db: Session = Depends(get_db)) -> LegalHoldRead:
    return lh_service.legal_holds.get(db, hold_id)


@router.get(
    "/legal-holds",
    response_model=ListResponse[LegalHoldRead],
)
def list_legal_holds(
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return lh_service.legal_holds.list_response(
        db, is_active, order_by, order_dir, limit, offset
    )


@router.patch(
    "/legal-holds/{hold_id}",
    response_model=LegalHoldRead,
)
def update_legal_hold(
    hold_id: str,
    payload: LegalHoldUpdate,
    db: Session = Depends(get_db),
) -> LegalHoldRead:
    return lh_service.legal_holds.update(db, hold_id, payload)


@router.delete(
    "/legal-holds/{hold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_legal_hold(hold_id: str, db: Session = Depends(get_db)) -> None:
    lh_service.legal_holds.delete(db, hold_id)


# ------------------------------------------------------------------
# LegalHoldDocument CRUD
# ------------------------------------------------------------------


@router.post(
    "/legal-hold-documents",
    response_model=LegalHoldDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_legal_hold_document(
    payload: LegalHoldDocumentCreate, db: Session = Depends(get_db)
) -> LegalHoldDocumentRead:
    return lh_service.legal_hold_documents.create(db, payload)


@router.get(
    "/legal-hold-documents/{lhd_id}",
    response_model=LegalHoldDocumentRead,
)
def get_legal_hold_document(
    lhd_id: str, db: Session = Depends(get_db)
) -> LegalHoldDocumentRead:
    return lh_service.legal_hold_documents.get(db, lhd_id)


@router.get(
    "/legal-hold-documents",
    response_model=ListResponse[LegalHoldDocumentRead],
)
def list_legal_hold_documents(
    legal_hold_id: str | None = None,
    document_id: str | None = None,
    added_by: str | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return lh_service.legal_hold_documents.list_response(
        db,
        legal_hold_id,
        document_id,
        added_by,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.delete(
    "/legal-hold-documents/{lhd_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_legal_hold_document(lhd_id: str, db: Session = Depends(get_db)) -> None:
    lh_service.legal_hold_documents.delete(db, lhd_id)
