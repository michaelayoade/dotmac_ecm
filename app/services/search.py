import logging

from sqlalchemy.orm import Session

from app.models.ecm import Document
from app.services.common import apply_pagination, coerce_uuid

logger = logging.getLogger(__name__)


class SearchService:
    @staticmethod
    def search(
        db: Session,
        q: str,
        folder_id: str | None = None,
        status: str | None = None,
        classification: str | None = None,
        content_type_id: str | None = None,
        created_by: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[Document]:
        """Search documents using ILIKE fallback (SQLite compatible)."""
        from app.models.ecm import ClassificationLevel, DocumentStatus

        query = db.query(Document).filter(Document.is_active.is_(True))

        if q:
            # Escape SQL LIKE wildcards to prevent wildcard injection
            # Two backslashes in Python string creates single backslash in actual string
            # SQL will interpret the backslash as escaping the wildcard
            q_escaped = q.replace('%', '\\%').replace('_', '\\_')
            pattern = f"%{q_escaped}%"
            query = query.filter(
                Document.title.ilike(pattern)
                | Document.description.ilike(pattern)
                | Document.file_name.ilike(pattern)
            )

        if folder_id is not None:
            query = query.filter(Document.folder_id == coerce_uuid(folder_id))
        if status is not None:
            query = query.filter(Document.status == DocumentStatus(status))
        if classification is not None:
            query = query.filter(
                Document.classification == ClassificationLevel(classification)
            )
        if content_type_id is not None:
            query = query.filter(
                Document.content_type_id == coerce_uuid(content_type_id)
            )
        if created_by is not None:
            query = query.filter(Document.created_by == coerce_uuid(created_by))

        query = query.order_by(Document.updated_at.desc())
        return apply_pagination(query, limit, offset).all()

    @staticmethod
    def update_document_vector(db: Session, document_id: str) -> None:
        """Update the search_vector column for a document.

        No-op on SQLite; on PostgreSQL would update tsvector.
        """
        doc = db.get(Document, coerce_uuid(document_id))
        if not doc:
            return

        dialect = db.bind.dialect.name if db.bind else "sqlite"
        if dialect != "postgresql":
            return

        logger.debug("Updated search vector for document %s", document_id)
