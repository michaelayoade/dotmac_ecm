from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_acl import (
    CheckinRequest,
    DocumentCheckoutCreate,
    DocumentCheckoutRead,
)
from app.services.ecm_checkout import checkouts

router = APIRouter(prefix="/ecm/documents", tags=["ecm-checkouts"])


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


@router.post(
    "/{document_id}/checkout",
    response_model=DocumentCheckoutRead,
    status_code=status.HTTP_201_CREATED,
)
def checkout_document(
    document_id: str,
    payload: DocumentCheckoutCreate,
    db: Session = Depends(get_db),
) -> DocumentCheckoutRead:
    return checkouts.checkout(
        db, document_id, str(payload.checked_out_by), payload.reason
    )


@router.get("/{document_id}/checkout", response_model=DocumentCheckoutRead)
def get_checkout(
    document_id: str, db: Session = Depends(get_db)
) -> DocumentCheckoutRead:
    return checkouts.get_checkout(db, document_id)


@router.post("/{document_id}/checkin", response_model=dict)
def checkin_document(
    document_id: str,
    payload: CheckinRequest,
    db: Session = Depends(get_db),
) -> dict:
    # person_id should come from auth context; for now accept from query
    # The checkin request body has change_summary, but person_id is needed
    # We use the checkout record's person to verify in service
    co = checkouts.get_checkout(db, document_id)
    checkouts.checkin(db, document_id, str(co.checked_out_by))
    return {"detail": "Document checked in successfully"}


@router.delete("/{document_id}/checkout", status_code=status.HTTP_204_NO_CONTENT)
def force_unlock(document_id: str, db: Session = Depends(get_db)) -> None:
    checkouts.force_unlock(db, document_id)


@router.get("/checkouts", response_model=ListResponse[DocumentCheckoutRead])
def list_checkouts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    items = checkouts.list_checkouts(db, limit, offset)
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}
