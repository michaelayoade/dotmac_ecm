from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.search import SearchResponse
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=SearchResponse)
def search_documents(
    q: str = Query(default="", min_length=0),
    folder_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    classification: str | None = None,
    content_type_id: str | None = None,
    created_by: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items = SearchService.search(
        db,
        q=q,
        folder_id=folder_id,
        status=status_filter,
        classification=classification,
        content_type_id=content_type_id,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}
