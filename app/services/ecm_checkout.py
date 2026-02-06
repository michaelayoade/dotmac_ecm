import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ecm import Document, DocumentCheckout
from app.models.person import Person
from app.services.common import apply_pagination, coerce_uuid
from app.services.event import EventType, publish_event

logger = logging.getLogger(__name__)


class Checkouts:
    @staticmethod
    def checkout(
        db: Session,
        document_id: str,
        person_id: str,
        reason: str | None = None,
    ) -> DocumentCheckout:
        doc_uuid = coerce_uuid(document_id)
        person_uuid = coerce_uuid(person_id)
        if not db.get(Document, doc_uuid):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(Person, person_uuid):
            raise HTTPException(status_code=404, detail="Person not found")

        checkout = DocumentCheckout(
            document_id=doc_uuid,
            checked_out_by=person_uuid,
            reason=reason,
        )
        try:
            db.add(checkout)
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409, detail="Document is already checked out"
            )
        db.flush()
        db.refresh(checkout)
        logger.info("Checked out document %s by person %s", document_id, person_id)
        publish_event(
            EventType.document_checked_out,
            entity_type="document_checkout",
            entity_id=checkout.id,
            actor_id=person_uuid,
            document_id=doc_uuid,
        )
        return checkout

    @staticmethod
    def get_checkout(db: Session, document_id: str) -> DocumentCheckout:
        doc_uuid = coerce_uuid(document_id)
        checkout = db.scalar(
            select(DocumentCheckout).where(DocumentCheckout.document_id == doc_uuid)
        )
        if not checkout:
            raise HTTPException(status_code=404, detail="Document is not checked out")
        return checkout

    @staticmethod
    def checkin(db: Session, document_id: str, person_id: str) -> None:
        doc_uuid = coerce_uuid(document_id)
        person_uuid = coerce_uuid(person_id)
        checkout = db.scalar(
            select(DocumentCheckout).where(DocumentCheckout.document_id == doc_uuid)
        )
        if not checkout:
            raise HTTPException(status_code=404, detail="Document is not checked out")
        if str(checkout.checked_out_by) != str(person_uuid):
            raise HTTPException(
                status_code=403,
                detail="Document is checked out by another person",
            )
        db.delete(checkout)
        db.flush()
        logger.info("Checked in document %s by person %s", document_id, person_id)
        publish_event(
            EventType.document_checked_in,
            entity_type="document_checkout",
            entity_id=doc_uuid,
            actor_id=person_uuid,
            document_id=doc_uuid,
        )

    @staticmethod
    def force_unlock(db: Session, document_id: str) -> None:
        doc_uuid = coerce_uuid(document_id)
        checkout = db.scalar(
            select(DocumentCheckout).where(DocumentCheckout.document_id == doc_uuid)
        )
        if not checkout:
            raise HTTPException(status_code=404, detail="Document is not checked out")
        db.delete(checkout)
        db.flush()
        logger.info("Force-unlocked document %s", document_id)

    @staticmethod
    def list_checkouts(db: Session, limit: int, offset: int) -> list[DocumentCheckout]:
        stmt = select(DocumentCheckout).order_by(DocumentCheckout.checked_out_at.desc())
        return db.scalars(apply_pagination(stmt, limit, offset)).all()


checkouts = Checkouts()
