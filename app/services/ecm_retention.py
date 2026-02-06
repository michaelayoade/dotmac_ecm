import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ecm import (
    Category,
    ContentType,
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentRetention,
    RetentionPolicy,
)
from app.models.person import Person
from app.schemas.ecm_retention import (
    DocumentRetentionCreate,
    DocumentRetentionUpdate,
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
)
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.event import EventType, publish_event
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


def _validate_disposition_action(action: str) -> None:
    try:
        DispositionAction(action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid disposition_action: {action}",
        )


def _validate_disposition_status(status: str) -> None:
    try:
        DispositionStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid disposition_status: {status}",
        )


# ---------------------------------------------------------------------------
# RetentionPolicies
# ---------------------------------------------------------------------------


class RetentionPolicies(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: RetentionPolicyCreate) -> RetentionPolicy:
        _validate_disposition_action(payload.disposition_action)
        if payload.content_type_id is not None:
            if not db.get(ContentType, coerce_uuid(payload.content_type_id)):
                raise HTTPException(status_code=404, detail="Content type not found")
        if payload.category_id is not None:
            if not db.get(Category, coerce_uuid(payload.category_id)):
                raise HTTPException(status_code=404, detail="Category not found")

        data = payload.model_dump()
        data["disposition_action"] = DispositionAction(data["disposition_action"])
        policy = RetentionPolicy(**data)
        db.add(policy)
        db.flush()
        db.refresh(policy)
        logger.info("Created retention policy %s", policy.id)
        return policy

    @staticmethod
    def get(db: Session, policy_id: str) -> RetentionPolicy:
        policy = db.get(RetentionPolicy, coerce_uuid(policy_id))
        if not policy:
            raise HTTPException(status_code=404, detail="Retention policy not found")
        return policy

    @staticmethod
    def list(
        db: Session,
        disposition_action: str | None,
        content_type_id: str | None,
        category_id: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[RetentionPolicy]:
        stmt = select(RetentionPolicy)
        if disposition_action is not None:
            stmt = stmt.where(
                RetentionPolicy.disposition_action
                == DispositionAction(disposition_action)
            )
        if content_type_id is not None:
            stmt = stmt.where(
                RetentionPolicy.content_type_id == coerce_uuid(content_type_id)
            )
        if category_id is not None:
            stmt = stmt.where(RetentionPolicy.category_id == coerce_uuid(category_id))
        if is_active is None:
            stmt = stmt.where(RetentionPolicy.is_active.is_(True))
        else:
            stmt = stmt.where(RetentionPolicy.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {
                "name": RetentionPolicy.name,
                "created_at": RetentionPolicy.created_at,
            },
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(
        db: Session,
        policy_id: str,
        payload: RetentionPolicyUpdate,
    ) -> RetentionPolicy:
        policy = db.get(RetentionPolicy, coerce_uuid(policy_id))
        if not policy:
            raise HTTPException(status_code=404, detail="Retention policy not found")
        data = payload.model_dump(exclude_unset=True)
        if "disposition_action" in data:
            _validate_disposition_action(data["disposition_action"])
            data["disposition_action"] = DispositionAction(data["disposition_action"])
        if "content_type_id" in data and data["content_type_id"] is not None:
            if not db.get(ContentType, coerce_uuid(data["content_type_id"])):
                raise HTTPException(status_code=404, detail="Content type not found")
        if "category_id" in data and data["category_id"] is not None:
            if not db.get(Category, coerce_uuid(data["category_id"])):
                raise HTTPException(status_code=404, detail="Category not found")
        for key, value in data.items():
            setattr(policy, key, value)
        db.flush()
        db.refresh(policy)
        logger.info("Updated retention policy %s", policy.id)
        return policy

    @staticmethod
    def delete(db: Session, policy_id: str) -> None:
        policy = db.get(RetentionPolicy, coerce_uuid(policy_id))
        if not policy:
            raise HTTPException(status_code=404, detail="Retention policy not found")
        policy.is_active = False
        db.flush()
        logger.info("Soft-deleted retention policy %s", policy_id)


# ---------------------------------------------------------------------------
# DocumentRetentions
# ---------------------------------------------------------------------------


class DocumentRetentions(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: DocumentRetentionCreate) -> DocumentRetention:
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(RetentionPolicy, coerce_uuid(payload.policy_id)):
            raise HTTPException(status_code=404, detail="Retention policy not found")
        _validate_disposition_status(payload.disposition_status)

        data = payload.model_dump()
        data["disposition_status"] = DispositionStatus(data["disposition_status"])
        retention = DocumentRetention(**data)
        db.add(retention)
        db.flush()
        db.refresh(retention)
        logger.info("Created document retention %s", retention.id)
        publish_event(
            EventType.retention_applied,
            entity_type="document_retention",
            entity_id=retention.id,
            document_id=retention.document_id,
        )
        return retention

    @staticmethod
    def get(db: Session, retention_id: str) -> DocumentRetention:
        retention = db.get(DocumentRetention, coerce_uuid(retention_id))
        if not retention:
            raise HTTPException(status_code=404, detail="Document retention not found")
        return retention

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        policy_id: str | None,
        disposition_status: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[DocumentRetention]:
        stmt = select(DocumentRetention)
        if document_id is not None:
            stmt = stmt.where(DocumentRetention.document_id == coerce_uuid(document_id))
        if policy_id is not None:
            stmt = stmt.where(DocumentRetention.policy_id == coerce_uuid(policy_id))
        if disposition_status is not None:
            stmt = stmt.where(
                DocumentRetention.disposition_status
                == DispositionStatus(disposition_status)
            )
        if is_active is None:
            stmt = stmt.where(DocumentRetention.is_active.is_(True))
        else:
            stmt = stmt.where(DocumentRetention.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {
                "created_at": DocumentRetention.created_at,
                "retention_expires_at": DocumentRetention.retention_expires_at,
            },
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(
        db: Session,
        retention_id: str,
        payload: DocumentRetentionUpdate,
    ) -> DocumentRetention:
        retention = db.get(DocumentRetention, coerce_uuid(retention_id))
        if not retention:
            raise HTTPException(status_code=404, detail="Document retention not found")
        data = payload.model_dump(exclude_unset=True)
        if "disposition_status" in data:
            _validate_disposition_status(data["disposition_status"])
            data["disposition_status"] = DispositionStatus(data["disposition_status"])
        for key, value in data.items():
            setattr(retention, key, value)
        db.flush()
        db.refresh(retention)
        logger.info("Updated document retention %s", retention.id)
        return retention

    @staticmethod
    def delete(db: Session, retention_id: str) -> None:
        retention = db.get(DocumentRetention, coerce_uuid(retention_id))
        if not retention:
            raise HTTPException(status_code=404, detail="Document retention not found")
        retention.is_active = False
        db.flush()
        logger.info("Soft-deleted document retention %s", retention_id)

    @staticmethod
    def dispose(db: Session, retention_id: str, disposed_by: str) -> DocumentRetention:
        retention = db.get(DocumentRetention, coerce_uuid(retention_id))
        if not retention:
            raise HTTPException(status_code=404, detail="Document retention not found")
        if retention.disposition_status == DispositionStatus.completed:
            raise HTTPException(status_code=400, detail="Retention already disposed")
        if not db.get(Person, coerce_uuid(disposed_by)):
            raise HTTPException(status_code=404, detail="Disposer not found")
        retention.disposition_status = DispositionStatus.completed
        retention.disposed_at = datetime.now(timezone.utc)
        retention.disposed_by = coerce_uuid(disposed_by)
        db.flush()
        db.refresh(retention)
        logger.info("Disposed document retention %s", retention.id)
        publish_event(
            EventType.retention_disposed,
            entity_type="document_retention",
            entity_id=retention.id,
            actor_id=retention.disposed_by,
            document_id=retention.document_id,
        )
        return retention


retention_policies = RetentionPolicies()
document_retentions = DocumentRetentions()
