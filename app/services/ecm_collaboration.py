import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import (
    Comment,
    CommentStatus,
    Document,
    DocumentSubscription,
)
from app.models.person import Person
from app.schemas.ecm_collaboration import (
    CommentCreate,
    CommentUpdate,
    DocumentSubscriptionCreate,
    DocumentSubscriptionUpdate,
)
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.event import EventType, publish_event
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


def _validate_comment_status(status: str) -> None:
    try:
        CommentStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}",
        )


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class Comments(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: CommentCreate) -> Comment:
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(Person, coerce_uuid(payload.author_id)):
            raise HTTPException(status_code=404, detail="Author not found")
        if payload.parent_id is not None:
            parent = db.get(Comment, coerce_uuid(payload.parent_id))
            if not parent:
                raise HTTPException(status_code=404, detail="Parent comment not found")
            if parent.document_id != coerce_uuid(payload.document_id):
                raise HTTPException(
                    status_code=400,
                    detail="Parent comment belongs to a different document",
                )
        _validate_comment_status(payload.status)

        data = payload.model_dump()
        data["status"] = CommentStatus(data["status"])
        comment = Comment(**data)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        logger.info("Created comment %s", comment.id)
        publish_event(
            EventType.comment_created,
            entity_type="comment",
            entity_id=comment.id,
            actor_id=comment.author_id,
            document_id=comment.document_id,
        )
        return comment

    @staticmethod
    def get(db: Session, comment_id: str) -> Comment:
        comment = db.get(Comment, coerce_uuid(comment_id))
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        return comment

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        author_id: str | None,
        parent_id: str | None,
        status: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[Comment]:
        query = db.query(Comment)
        if document_id is not None:
            query = query.filter(Comment.document_id == coerce_uuid(document_id))
        if author_id is not None:
            query = query.filter(Comment.author_id == coerce_uuid(author_id))
        if parent_id is not None:
            query = query.filter(Comment.parent_id == coerce_uuid(parent_id))
        if status is not None:
            query = query.filter(Comment.status == CommentStatus(status))
        if is_active is None:
            query = query.filter(Comment.is_active.is_(True))
        else:
            query = query.filter(Comment.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": Comment.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(db: Session, comment_id: str, payload: CommentUpdate) -> Comment:
        comment = db.get(Comment, coerce_uuid(comment_id))
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        data = payload.model_dump(exclude_unset=True)
        if "status" in data:
            _validate_comment_status(data["status"])
            data["status"] = CommentStatus(data["status"])
        for key, value in data.items():
            setattr(comment, key, value)
        db.commit()
        db.refresh(comment)
        logger.info("Updated comment %s", comment.id)
        publish_event(
            EventType.comment_updated,
            entity_type="comment",
            entity_id=comment.id,
            actor_id=comment.author_id,
            document_id=comment.document_id,
        )
        return comment

    @staticmethod
    def delete(db: Session, comment_id: str) -> None:
        comment = db.get(Comment, coerce_uuid(comment_id))
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        doc_id = comment.document_id
        comment.is_active = False
        db.commit()
        logger.info("Soft-deleted comment %s", comment_id)
        publish_event(
            EventType.comment_deleted,
            entity_type="comment",
            entity_id=comment_id,
            document_id=doc_id,
        )


# ---------------------------------------------------------------------------
# DocumentSubscriptions
# ---------------------------------------------------------------------------


class DocumentSubscriptions(ListResponseMixin):
    @staticmethod
    def create(
        db: Session, payload: DocumentSubscriptionCreate
    ) -> DocumentSubscription:
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        if not db.get(Person, coerce_uuid(payload.person_id)):
            raise HTTPException(status_code=404, detail="Person not found")

        data = payload.model_dump()
        sub = DocumentSubscription(**data)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info("Created document subscription %s", sub.id)
        return sub

    @staticmethod
    def get(db: Session, subscription_id: str) -> DocumentSubscription:
        sub = db.get(DocumentSubscription, coerce_uuid(subscription_id))
        if not sub:
            raise HTTPException(
                status_code=404, detail="Document subscription not found"
            )
        return sub

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        person_id: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[DocumentSubscription]:
        query = db.query(DocumentSubscription)
        if document_id is not None:
            query = query.filter(
                DocumentSubscription.document_id == coerce_uuid(document_id)
            )
        if person_id is not None:
            query = query.filter(
                DocumentSubscription.person_id == coerce_uuid(person_id)
            )
        if is_active is None:
            query = query.filter(DocumentSubscription.is_active.is_(True))
        else:
            query = query.filter(DocumentSubscription.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"created_at": DocumentSubscription.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session,
        subscription_id: str,
        payload: DocumentSubscriptionUpdate,
    ) -> DocumentSubscription:
        sub = db.get(DocumentSubscription, coerce_uuid(subscription_id))
        if not sub:
            raise HTTPException(
                status_code=404, detail="Document subscription not found"
            )
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(sub, key, value)
        db.commit()
        db.refresh(sub)
        logger.info("Updated document subscription %s", sub.id)
        return sub

    @staticmethod
    def delete(db: Session, subscription_id: str) -> None:
        sub = db.get(DocumentSubscription, coerce_uuid(subscription_id))
        if not sub:
            raise HTTPException(
                status_code=404, detail="Document subscription not found"
            )
        sub.is_active = False
        db.commit()
        logger.info("Soft-deleted document subscription %s", subscription_id)


comments = Comments()
document_subscriptions = DocumentSubscriptions()
