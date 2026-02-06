from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ContentTypeCreate,
    ContentTypeRead,
    ContentTypeUpdate,
    DocumentCategoryCreate,
    DocumentCategoryRead,
    DocumentTagCreate,
    DocumentTagRead,
    TagCreate,
    TagRead,
    TagUpdate,
)
from app.services import ecm_metadata as meta_service

router = APIRouter(prefix="/ecm", tags=["ecm-metadata"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# ContentType CRUD
# ------------------------------------------------------------------


@router.post(
    "/content-types",
    response_model=ContentTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_content_type(payload: ContentTypeCreate, db: Session = Depends(get_db)):
    return meta_service.content_types.create(db, payload)


@router.get("/content-types/{content_type_id}", response_model=ContentTypeRead)
def get_content_type(content_type_id: str, db: Session = Depends(get_db)):
    return meta_service.content_types.get(db, content_type_id)


@router.get("/content-types", response_model=ListResponse[ContentTypeRead])
def list_content_types(
    is_active: bool | None = None,
    order_by: str = Query(default="name"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return meta_service.content_types.list_response(
        db, is_active, order_by, order_dir, limit, offset
    )


@router.patch("/content-types/{content_type_id}", response_model=ContentTypeRead)
def update_content_type(
    content_type_id: str,
    payload: ContentTypeUpdate,
    db: Session = Depends(get_db),
):
    return meta_service.content_types.update(db, content_type_id, payload)


@router.delete(
    "/content-types/{content_type_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_content_type(content_type_id: str, db: Session = Depends(get_db)):
    meta_service.content_types.delete(db, content_type_id)


# ------------------------------------------------------------------
# Tag CRUD
# ------------------------------------------------------------------


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    return meta_service.tags.create(db, payload)


@router.get("/tags/{tag_id}", response_model=TagRead)
def get_tag(tag_id: str, db: Session = Depends(get_db)):
    return meta_service.tags.get(db, tag_id)


@router.get("/tags", response_model=ListResponse[TagRead])
def list_tags(
    is_active: bool | None = None,
    order_by: str = Query(default="name"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return meta_service.tags.list_response(
        db, is_active, order_by, order_dir, limit, offset
    )


@router.patch("/tags/{tag_id}", response_model=TagRead)
def update_tag(tag_id: str, payload: TagUpdate, db: Session = Depends(get_db)):
    return meta_service.tags.update(db, tag_id, payload)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    meta_service.tags.delete(db, tag_id)


# ------------------------------------------------------------------
# DocumentTag (junction)
# ------------------------------------------------------------------


@router.post(
    "/document-tags",
    response_model=DocumentTagRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_tag(payload: DocumentTagCreate, db: Session = Depends(get_db)):
    return meta_service.document_tags.create(db, payload)


@router.get("/document-tags/{link_id}", response_model=DocumentTagRead)
def get_document_tag(link_id: str, db: Session = Depends(get_db)):
    return meta_service.document_tags.get(db, link_id)


@router.get("/document-tags", response_model=ListResponse[DocumentTagRead])
def list_document_tags(
    document_id: str | None = None,
    tag_id: str | None = None,
    order_by: str = Query(default="document_id"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return meta_service.document_tags.list_response(
        db, document_id, tag_id, order_by, order_dir, limit, offset
    )


@router.delete("/document-tags/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_tag(link_id: str, db: Session = Depends(get_db)):
    meta_service.document_tags.delete(db, link_id)


# ------------------------------------------------------------------
# Category CRUD (hierarchical)
# ------------------------------------------------------------------


@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    return meta_service.categories.create(db, payload)


@router.get("/categories/{category_id}", response_model=CategoryRead)
def get_category(category_id: str, db: Session = Depends(get_db)):
    return meta_service.categories.get(db, category_id)


@router.get("/categories", response_model=ListResponse[CategoryRead])
def list_categories(
    parent_id: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="name"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return meta_service.categories.list_response(
        db, parent_id, is_active, order_by, order_dir, limit, offset
    )


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str, payload: CategoryUpdate, db: Session = Depends(get_db)
):
    return meta_service.categories.update(db, category_id, payload)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, db: Session = Depends(get_db)):
    meta_service.categories.delete(db, category_id)


# ------------------------------------------------------------------
# DocumentCategory (junction)
# ------------------------------------------------------------------


@router.post(
    "/document-categories",
    response_model=DocumentCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_category(
    payload: DocumentCategoryCreate, db: Session = Depends(get_db)
):
    return meta_service.document_categories.create(db, payload)


@router.get("/document-categories/{link_id}", response_model=DocumentCategoryRead)
def get_document_category(link_id: str, db: Session = Depends(get_db)):
    return meta_service.document_categories.get(db, link_id)


@router.get("/document-categories", response_model=ListResponse[DocumentCategoryRead])
def list_document_categories(
    document_id: str | None = None,
    category_id: str | None = None,
    order_by: str = Query(default="document_id"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return meta_service.document_categories.list_response(
        db, document_id, category_id, order_by, order_dir, limit, offset
    )


@router.delete("/document-categories/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_category(link_id: str, db: Session = Depends(get_db)):
    meta_service.document_categories.delete(db, link_id)
