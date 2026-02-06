from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm_collaboration import (
    CommentCreate,
    CommentRead,
    CommentUpdate,
    DocumentSubscriptionCreate,
    DocumentSubscriptionRead,
    DocumentSubscriptionUpdate,
)
from app.services import ecm_collaboration as collab_service

router = APIRouter(prefix="/ecm", tags=["ecm-collaboration"])


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
# Comment CRUD
# ------------------------------------------------------------------


@router.post(
    "/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    payload: CommentCreate, db: Session = Depends(get_db)
) -> CommentRead:
    return collab_service.comments.create(db, payload)


@router.get("/comments/{comment_id}", response_model=CommentRead)
def get_comment(comment_id: str, db: Session = Depends(get_db)) -> CommentRead:
    return collab_service.comments.get(db, comment_id)


@router.get("/comments", response_model=ListResponse[CommentRead])
def list_comments(
    document_id: str | None = None,
    author_id: str | None = None,
    parent_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return collab_service.comments.list_response(
        db,
        document_id,
        author_id,
        parent_id,
        status_filter,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch("/comments/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: str, payload: CommentUpdate, db: Session = Depends(get_db)
) -> CommentRead:
    return collab_service.comments.update(db, comment_id, payload)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: str, db: Session = Depends(get_db)) -> None:
    collab_service.comments.delete(db, comment_id)


# ------------------------------------------------------------------
# DocumentSubscription CRUD
# ------------------------------------------------------------------


@router.post(
    "/document-subscriptions",
    response_model=DocumentSubscriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_subscription(
    payload: DocumentSubscriptionCreate, db: Session = Depends(get_db)
) -> DocumentSubscriptionRead:
    return collab_service.document_subscriptions.create(db, payload)


@router.get(
    "/document-subscriptions/{subscription_id}",
    response_model=DocumentSubscriptionRead,
)
def get_document_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> DocumentSubscriptionRead:
    return collab_service.document_subscriptions.get(db, subscription_id)


@router.get(
    "/document-subscriptions",
    response_model=ListResponse[DocumentSubscriptionRead],
)
def list_document_subscriptions(
    document_id: str | None = None,
    person_id: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="created_at"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return collab_service.document_subscriptions.list_response(
        db,
        document_id,
        person_id,
        is_active,
        order_by,
        order_dir,
        limit,
        offset,
    )


@router.patch(
    "/document-subscriptions/{subscription_id}",
    response_model=DocumentSubscriptionRead,
)
def update_document_subscription(
    subscription_id: str,
    payload: DocumentSubscriptionUpdate,
    db: Session = Depends(get_db),
) -> DocumentSubscriptionRead:
    return collab_service.document_subscriptions.update(db, subscription_id, payload)


@router.delete(
    "/document-subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> None:
    collab_service.document_subscriptions.delete(db, subscription_id)
