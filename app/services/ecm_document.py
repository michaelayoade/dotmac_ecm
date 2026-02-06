from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ecm import (
    ClassificationLevel,
    ContentType,
    Document,
    DocumentStatus,
    DocumentVersion,
    Folder,
)
from app.models.person import Person
from app.schemas.ecm import DocumentCreate, DocumentUpdate, DocumentVersionCreate
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.event import EventType, publish_event
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)

_VALID_CLASSIFICATIONS = {e.value for e in ClassificationLevel}
_VALID_STATUSES = {e.value for e in DocumentStatus}


class Documents(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: DocumentCreate) -> Document:
        creator = db.get(Person, coerce_uuid(payload.created_by))
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")

        if payload.folder_id:
            folder = db.get(Folder, coerce_uuid(payload.folder_id))
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")

        if payload.content_type_id:
            ct = db.get(ContentType, coerce_uuid(payload.content_type_id))
            if not ct:
                raise HTTPException(status_code=404, detail="Content type not found")

        if payload.classification not in _VALID_CLASSIFICATIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid classification. Allowed: {sorted(_VALID_CLASSIFICATIONS)}",
            )
        if payload.status not in _VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Allowed: {sorted(_VALID_STATUSES)}",
            )

        data = payload.model_dump()
        data["classification"] = ClassificationLevel(data["classification"])
        data["status"] = DocumentStatus(data["status"])

        document = Document(**data)
        db.add(document)
        db.flush()
        db.refresh(document)
        logger.info("Created document %s", document.id)
        publish_event(
            EventType.document_created,
            entity_type="document",
            entity_id=document.id,
            actor_id=document.created_by,
            document_id=document.id,
        )
        return document

    @staticmethod
    def get(db: Session, document_id: str) -> Document:
        document = db.get(Document, coerce_uuid(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    @staticmethod
    def list(
        db: Session,
        folder_id: str | None,
        status: str | None,
        classification: str | None,
        content_type_id: str | None,
        created_by: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[Document]:  # type: ignore[override]
        stmt = select(Document)
        if folder_id is not None:
            stmt = stmt.where(Document.folder_id == coerce_uuid(folder_id))
        if status is not None:
            stmt = stmt.where(Document.status == DocumentStatus(status))
        if classification is not None:
            stmt = stmt.where(
                Document.classification == ClassificationLevel(classification)
            )
        if content_type_id is not None:
            stmt = stmt.where(Document.content_type_id == coerce_uuid(content_type_id))
        if created_by is not None:
            stmt = stmt.where(Document.created_by == coerce_uuid(created_by))
        if is_active is None:
            stmt = stmt.where(Document.is_active.is_(True))
        else:
            stmt = stmt.where(Document.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {
                "created_at": Document.created_at,
                "title": Document.title,
                "updated_at": Document.updated_at,
                "file_size": Document.file_size,
            },
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(db: Session, document_id: str, payload: DocumentUpdate) -> Document:
        document = db.get(Document, coerce_uuid(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        data = payload.model_dump(exclude_unset=True)

        if "folder_id" in data and data["folder_id"] is not None:
            folder = db.get(Folder, coerce_uuid(data["folder_id"]))
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")

        if "content_type_id" in data and data["content_type_id"] is not None:
            ct = db.get(ContentType, coerce_uuid(data["content_type_id"]))
            if not ct:
                raise HTTPException(status_code=404, detail="Content type not found")

        if "classification" in data and data["classification"] is not None:
            if data["classification"] not in _VALID_CLASSIFICATIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid classification. Allowed: {sorted(_VALID_CLASSIFICATIONS)}",
                )
            data["classification"] = ClassificationLevel(data["classification"])

        if "status" in data and data["status"] is not None:
            if data["status"] not in _VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Allowed: {sorted(_VALID_STATUSES)}",
                )
            data["status"] = DocumentStatus(data["status"])

        for key, value in data.items():
            setattr(document, key, value)

        db.flush()
        db.refresh(document)
        logger.info("Updated document %s", document.id)
        event_type = EventType.document_updated
        if "status" in data:
            event_type = EventType.document_status_changed
        publish_event(
            event_type,
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
            payload={"changed_fields": list(data.keys())},
        )
        return document

    @staticmethod
    def delete(db: Session, document_id: str) -> None:
        document = db.get(Document, coerce_uuid(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        document.is_active = False
        db.flush()
        logger.info("Soft-deleted document %s", document.id)
        publish_event(
            EventType.document_deleted,
            entity_type="document",
            entity_id=document.id,
            document_id=document.id,
        )

    # ------------------------------------------------------------------
    # Version sub-operations
    # ------------------------------------------------------------------

    @staticmethod
    def create_version(
        db: Session, document_id: str, payload: DocumentVersionCreate
    ) -> DocumentVersion:
        document = db.get(Document, coerce_uuid(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        creator = db.get(Person, coerce_uuid(payload.created_by))
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")

        next_version = document.version_number + 1
        version = DocumentVersion(
            document_id=document.id,
            version_number=next_version,
            file_name=payload.file_name,
            file_size=payload.file_size,
            mime_type=payload.mime_type,
            storage_key=payload.storage_key,
            checksum_sha256=payload.checksum_sha256,
            change_summary=payload.change_summary,
            created_by=payload.created_by,
        )
        db.add(version)
        db.flush()

        document.current_version_id = version.id
        document.version_number = next_version
        document.file_name = version.file_name
        document.file_size = version.file_size
        document.mime_type = version.mime_type
        document.storage_key = version.storage_key
        document.checksum_sha256 = version.checksum_sha256

        db.flush()
        db.refresh(version)
        logger.info(
            "Created version %s (v%d) for document %s",
            version.id,
            next_version,
            document.id,
        )
        publish_event(
            EventType.version_created,
            entity_type="document_version",
            entity_id=version.id,
            actor_id=version.created_by,
            document_id=document.id,
            payload={"version_number": next_version},
        )
        return version

    @staticmethod
    def get_version(db: Session, document_id: str, version_id: str) -> DocumentVersion:
        version = db.get(DocumentVersion, coerce_uuid(version_id))
        if not version or str(version.document_id) != str(coerce_uuid(document_id)):
            raise HTTPException(status_code=404, detail="Document version not found")
        return version

    @staticmethod
    def list_versions(
        db: Session,
        document_id: str,
        limit: int,
        offset: int,
    ) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == coerce_uuid(document_id))
            .where(DocumentVersion.is_active.is_(True))
            .order_by(DocumentVersion.version_number.desc())
            .limit(limit)
            .offset(offset)
        )
        return db.scalars(stmt).all()

    @staticmethod
    def delete_version(db: Session, document_id: str, version_id: str) -> None:
        version = db.get(DocumentVersion, coerce_uuid(version_id))
        if not version or str(version.document_id) != str(coerce_uuid(document_id)):
            raise HTTPException(status_code=404, detail="Document version not found")

        document = db.get(Document, coerce_uuid(document_id))
        if document and document.current_version_id == version.id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the current version of a document",
            )

        version.is_active = False
        db.flush()
        logger.info("Soft-deleted version %s for document %s", version_id, document_id)
        publish_event(
            EventType.version_deleted,
            entity_type="document_version",
            entity_id=version_id,
            document_id=document_id,
        )


documents = Documents()
