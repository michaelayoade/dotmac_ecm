import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ecm import (
    Category,
    ContentType,
    Document,
    DocumentCategory,
    DocumentTag,
    Tag,
)
from app.schemas.ecm import (
    CategoryCreate,
    CategoryUpdate,
    ContentTypeCreate,
    ContentTypeUpdate,
    DocumentCategoryCreate,
    DocumentTagCreate,
    TagCreate,
    TagUpdate,
)
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ContentTypes
# ---------------------------------------------------------------------------


class ContentTypes(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: ContentTypeCreate) -> ContentType:
        data = payload.model_dump(by_alias=False)
        if "schema_" in data:
            data["schema"] = data.pop("schema_")
        ct = ContentType(**data)
        db.add(ct)
        db.commit()
        db.refresh(ct)
        logger.info("Created content type %s", ct.id)
        return ct

    @staticmethod
    def get(db: Session, content_type_id: str) -> ContentType:
        ct = db.get(ContentType, coerce_uuid(content_type_id))
        if not ct:
            raise HTTPException(status_code=404, detail="Content type not found")
        return ct

    @staticmethod
    def list(
        db: Session,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[ContentType]:
        query = db.query(ContentType)
        if is_active is None:
            query = query.filter(ContentType.is_active.is_(True))
        else:
            query = query.filter(ContentType.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"name": ContentType.name, "created_at": ContentType.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(
        db: Session, content_type_id: str, payload: ContentTypeUpdate
    ) -> ContentType:
        ct = db.get(ContentType, coerce_uuid(content_type_id))
        if not ct:
            raise HTTPException(status_code=404, detail="Content type not found")
        data = payload.model_dump(exclude_unset=True, by_alias=False)
        if "schema_" in data:
            data["schema"] = data.pop("schema_")
        for key, value in data.items():
            setattr(ct, key, value)
        db.commit()
        db.refresh(ct)
        logger.info("Updated content type %s", ct.id)
        return ct

    @staticmethod
    def delete(db: Session, content_type_id: str) -> None:
        ct = db.get(ContentType, coerce_uuid(content_type_id))
        if not ct:
            raise HTTPException(status_code=404, detail="Content type not found")
        ct.is_active = False
        db.commit()
        logger.info("Soft-deleted content type %s", content_type_id)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class Tags(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: TagCreate) -> Tag:
        tag = Tag(**payload.model_dump())
        db.add(tag)
        db.commit()
        db.refresh(tag)
        logger.info("Created tag %s", tag.id)
        return tag

    @staticmethod
    def get(db: Session, tag_id: str) -> Tag:
        tag = db.get(Tag, coerce_uuid(tag_id))
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        return tag

    @staticmethod
    def list(
        db: Session,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[Tag]:
        query = db.query(Tag)
        if is_active is None:
            query = query.filter(Tag.is_active.is_(True))
        else:
            query = query.filter(Tag.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"name": Tag.name, "created_at": Tag.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(db: Session, tag_id: str, payload: TagUpdate) -> Tag:
        tag = db.get(Tag, coerce_uuid(tag_id))
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(tag, key, value)
        db.commit()
        db.refresh(tag)
        logger.info("Updated tag %s", tag.id)
        return tag

    @staticmethod
    def delete(db: Session, tag_id: str) -> None:
        tag = db.get(Tag, coerce_uuid(tag_id))
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        tag.is_active = False
        db.commit()
        logger.info("Soft-deleted tag %s", tag_id)


# ---------------------------------------------------------------------------
# DocumentTags (junction — hard delete)
# ---------------------------------------------------------------------------


class DocumentTags(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: DocumentTagCreate) -> DocumentTag:
        document = db.get(Document, coerce_uuid(payload.document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        tag = db.get(Tag, coerce_uuid(payload.tag_id))
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        link = DocumentTag(**payload.model_dump())
        db.add(link)
        db.commit()
        db.refresh(link)
        logger.info("Created document-tag link %s", link.id)
        return link

    @staticmethod
    def get(db: Session, link_id: str) -> DocumentTag:
        link = db.get(DocumentTag, coerce_uuid(link_id))
        if not link:
            raise HTTPException(status_code=404, detail="Document tag not found")
        return link

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        tag_id: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[DocumentTag]:
        query = db.query(DocumentTag)
        if document_id is not None:
            query = query.filter(DocumentTag.document_id == coerce_uuid(document_id))
        if tag_id is not None:
            query = query.filter(DocumentTag.tag_id == coerce_uuid(tag_id))
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"document_id": DocumentTag.document_id},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def delete(db: Session, link_id: str) -> None:
        link = db.get(DocumentTag, coerce_uuid(link_id))
        if not link:
            raise HTTPException(status_code=404, detail="Document tag not found")
        db.delete(link)
        db.commit()
        logger.info("Deleted document-tag link %s", link_id)


# ---------------------------------------------------------------------------
# Categories (hierarchical)
# ---------------------------------------------------------------------------


class Categories(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: CategoryCreate) -> Category:
        if payload.parent_id:
            parent = db.get(Category, coerce_uuid(payload.parent_id))
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

        category = Category(**payload.model_dump())
        db.add(category)
        db.flush()

        category.path = Categories._compute_path(db, category)
        category.depth = Categories._compute_depth(category.path)

        db.commit()
        db.refresh(category)
        logger.info("Created category %s", category.id)
        return category

    @staticmethod
    def get(db: Session, category_id: str) -> Category:
        category = db.get(Category, coerce_uuid(category_id))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category

    @staticmethod
    def list(
        db: Session,
        parent_id: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[Category]:
        query = db.query(Category)
        if parent_id is not None:
            query = query.filter(Category.parent_id == coerce_uuid(parent_id))
        if is_active is None:
            query = query.filter(Category.is_active.is_(True))
        else:
            query = query.filter(Category.is_active == is_active)
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"name": Category.name, "created_at": Category.created_at},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update(db: Session, category_id: str, payload: CategoryUpdate) -> Category:
        category = db.get(Category, coerce_uuid(category_id))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        data = payload.model_dump(exclude_unset=True)
        old_parent_id = category.parent_id

        if "parent_id" in data and data["parent_id"] is not None:
            parent = db.get(Category, coerce_uuid(data["parent_id"]))
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

        for key, value in data.items():
            setattr(category, key, value)

        parent_changed = "parent_id" in data and data.get("parent_id") != old_parent_id
        name_changed = "name" in data

        if parent_changed or name_changed:
            old_path = category.path
            category.path = Categories._compute_path(db, category)
            category.depth = Categories._compute_depth(category.path)
            if parent_changed:
                Categories._recompute_subtree_paths(db, category, old_path)

        db.commit()
        db.refresh(category)
        logger.info("Updated category %s", category.id)
        return category

    @staticmethod
    def delete(db: Session, category_id: str) -> None:
        category = db.get(Category, coerce_uuid(category_id))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        category.is_active = False
        db.commit()
        logger.info("Soft-deleted category %s", category_id)

    @staticmethod
    def _compute_path(db: Session, category: Category) -> str:
        if category.parent_id is None:
            return f"/{category.name}"
        parent = db.get(Category, category.parent_id)
        if not parent:
            return f"/{category.name}"
        return f"{parent.path}/{category.name}"

    @staticmethod
    def _compute_depth(path: str) -> int:
        return path.count("/") - 1

    @staticmethod
    def _recompute_subtree_paths(
        db: Session, category: Category, old_path: str
    ) -> None:
        descendants = (
            db.query(Category).filter(Category.path.like(f"{old_path}/%")).all()
        )
        for child in descendants:
            child.path = category.path + child.path[len(old_path) :]
            child.depth = Categories._compute_depth(child.path)


# ---------------------------------------------------------------------------
# DocumentCategories (junction — hard delete)
# ---------------------------------------------------------------------------


class DocumentCategories(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: DocumentCategoryCreate) -> DocumentCategory:
        document = db.get(Document, coerce_uuid(payload.document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        category = db.get(Category, coerce_uuid(payload.category_id))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        link = DocumentCategory(**payload.model_dump())
        db.add(link)
        db.commit()
        db.refresh(link)
        logger.info("Created document-category link %s", link.id)
        return link

    @staticmethod
    def get(db: Session, link_id: str) -> DocumentCategory:
        link = db.get(DocumentCategory, coerce_uuid(link_id))
        if not link:
            raise HTTPException(status_code=404, detail="Document category not found")
        return link

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        category_id: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[DocumentCategory]:
        query = db.query(DocumentCategory)
        if document_id is not None:
            query = query.filter(
                DocumentCategory.document_id == coerce_uuid(document_id)
            )
        if category_id is not None:
            query = query.filter(
                DocumentCategory.category_id == coerce_uuid(category_id)
            )
        query = apply_ordering(
            query,
            order_by,
            order_dir,
            {"document_id": DocumentCategory.document_id},
        )
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def delete(db: Session, link_id: str) -> None:
        link = db.get(DocumentCategory, coerce_uuid(link_id))
        if not link:
            raise HTTPException(status_code=404, detail="Document category not found")
        db.delete(link)
        db.commit()
        logger.info("Deleted document-category link %s", link_id)


content_types = ContentTypes()
tags = Tags()
document_tags = DocumentTags()
categories = Categories()
document_categories = DocumentCategories()
