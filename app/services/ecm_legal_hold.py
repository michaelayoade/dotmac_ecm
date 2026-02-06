import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import Document, LegalHold, LegalHoldDocument
from app.models.person import Person
from app.schemas.ecm_legal_hold import (
    LegalHoldCreate,
    LegalHoldDocumentCreate,
    LegalHoldUpdate,
)
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LegalHolds
# ---------------------------------------------------------------------------


class LegalHolds(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: LegalHoldCreate) -> LegalHold:
        if not db.get(Person, coerce_uuid(payload.created_by)):
            raise HTTPException(status_code=404, detail="Creator not found")

        data = payload.model_dump()
        hold = LegalHold(**data)
        db.add(hold)
        db.commit()
        db.refresh(hold)
        logger.info("Created legal hold %s", hold.id)
        return hold

    @staticmethod
    def get(db: Session, hold_id: str) -> LegalHold:
        hold = db.get(LegalHold, coerce_uuid(hold_id))
        if not hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        return hold

    @staticmethod
    def list(
        db: Session,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[LegalHold]:
        query = db.query(LegalHold)
        if is_active is None:
            query = query.filter(LegalHold.is_active.is_(True))
        else:
            query = query.filter(LegalHold.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {
                "name": LegalHold.name,
                "created_at": LegalHold.created_at,
            },
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session,
        hold_id: str,
        payload: LegalHoldUpdate,
    ) -> LegalHold:
        hold = db.get(LegalHold, coerce_uuid(hold_id))
        if not hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(hold, key, value)
        db.commit()
        db.refresh(hold)
        logger.info("Updated legal hold %s", hold.id)
        return hold

    @staticmethod
    def delete(db: Session, hold_id: str) -> None:
        hold = db.get(LegalHold, coerce_uuid(hold_id))
        if not hold:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        hold.is_active = False
        db.commit()
        logger.info("Soft-deleted legal hold %s", hold_id)


# ---------------------------------------------------------------------------
# LegalHoldDocuments
# ---------------------------------------------------------------------------


class LegalHoldDocuments(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: LegalHoldDocumentCreate) -> LegalHoldDocument:
        if not db.get(LegalHold, coerce_uuid(payload.legal_hold_id)):
            raise HTTPException(status_code=404, detail="Legal hold not found")
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(Person, coerce_uuid(payload.added_by)):
            raise HTTPException(status_code=404, detail="Adder not found")

        data = payload.model_dump()
        lhd = LegalHoldDocument(**data)
        db.add(lhd)
        db.commit()
        db.refresh(lhd)
        logger.info("Created legal hold document %s", lhd.id)
        return lhd

    @staticmethod
    def get(db: Session, lhd_id: str) -> LegalHoldDocument:
        lhd = db.get(LegalHoldDocument, coerce_uuid(lhd_id))
        if not lhd:
            raise HTTPException(status_code=404, detail="Legal hold document not found")
        return lhd

    @staticmethod
    def list(
        db: Session,
        legal_hold_id: str | None,
        document_id: str | None,
        added_by: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[LegalHoldDocument]:
        query = db.query(LegalHoldDocument)
        if legal_hold_id is not None:
            query = query.filter(
                LegalHoldDocument.legal_hold_id == coerce_uuid(legal_hold_id)
            )
        if document_id is not None:
            query = query.filter(
                LegalHoldDocument.document_id == coerce_uuid(document_id)
            )
        if added_by is not None:
            query = query.filter(LegalHoldDocument.added_by == coerce_uuid(added_by))
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": LegalHoldDocument.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def delete(db: Session, lhd_id: str) -> None:
        lhd = db.get(LegalHoldDocument, coerce_uuid(lhd_id))
        if not lhd:
            raise HTTPException(status_code=404, detail="Legal hold document not found")
        db.delete(lhd)
        db.commit()
        logger.info("Deleted legal hold document %s", lhd_id)


legal_holds = LegalHolds()
legal_hold_documents = LegalHoldDocuments()
