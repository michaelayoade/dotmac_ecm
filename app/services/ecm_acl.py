import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ecm import (
    ACLPermission,
    Document,
    DocumentACL,
    Folder,
    FolderACL,
    PrincipalType,
)
from app.models.person import Person
from app.models.rbac import Role
from app.schemas.ecm_acl import (
    DocumentACLCreate,
    DocumentACLUpdate,
    FolderACLCreate,
    FolderACLUpdate,
)
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.event import EventType, publish_event
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


def _validate_principal(db: Session, principal_type: str, principal_id: str) -> None:
    try:
        PrincipalType(principal_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid principal_type: {principal_type}",
        )
    pid = coerce_uuid(principal_id)
    if principal_type == "person":
        if not db.get(Person, pid):
            raise HTTPException(status_code=404, detail="Person not found")
    elif principal_type == "role":
        if not db.get(Role, pid):
            raise HTTPException(status_code=404, detail="Role not found")


def _validate_permission(permission: str) -> None:
    try:
        ACLPermission(permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission: {permission}",
        )


def _validate_grantor(db: Session, granted_by: str) -> None:
    if not db.get(Person, coerce_uuid(granted_by)):
        raise HTTPException(status_code=404, detail="Grantor not found")


# ---------------------------------------------------------------------------
# DocumentACLs
# ---------------------------------------------------------------------------


class DocumentACLs(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: DocumentACLCreate) -> DocumentACL:
        if not db.get(Document, coerce_uuid(payload.document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
        _validate_principal(db, payload.principal_type, str(payload.principal_id))
        _validate_permission(payload.permission)
        _validate_grantor(db, str(payload.granted_by))

        data = payload.model_dump()
        data["principal_type"] = PrincipalType(data["principal_type"])
        data["permission"] = ACLPermission(data["permission"])
        acl = DocumentACL(**data)
        db.add(acl)
        db.flush()
        db.refresh(acl)
        logger.info("Created document ACL %s", acl.id)
        publish_event(
            EventType.acl_granted,
            entity_type="document_acl",
            entity_id=acl.id,
            actor_id=acl.granted_by,
            document_id=acl.document_id,
            payload={"permission": acl.permission.value},
        )
        return acl

    @staticmethod
    def get(db: Session, acl_id: str) -> DocumentACL:
        acl = db.get(DocumentACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Document ACL not found")
        return acl

    @staticmethod
    def list(
        db: Session,
        document_id: str | None,
        principal_type: str | None,
        principal_id: str | None,
        permission: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[DocumentACL]:
        stmt = select(DocumentACL)
        if document_id is not None:
            stmt = stmt.where(DocumentACL.document_id == coerce_uuid(document_id))
        if principal_type is not None:
            stmt = stmt.where(
                DocumentACL.principal_type == PrincipalType(principal_type)
            )
        if principal_id is not None:
            stmt = stmt.where(DocumentACL.principal_id == coerce_uuid(principal_id))
        if permission is not None:
            stmt = stmt.where(DocumentACL.permission == ACLPermission(permission))
        if is_active is None:
            stmt = stmt.where(DocumentACL.is_active.is_(True))
        else:
            stmt = stmt.where(DocumentACL.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {"created_at": DocumentACL.created_at},
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(db: Session, acl_id: str, payload: DocumentACLUpdate) -> DocumentACL:
        acl = db.get(DocumentACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Document ACL not found")
        data = payload.model_dump(exclude_unset=True)
        if "principal_type" in data:
            _validate_principal(
                db,
                data["principal_type"],
                str(data.get("principal_id", acl.principal_id)),
            )
            data["principal_type"] = PrincipalType(data["principal_type"])
        if "principal_id" in data and "principal_type" not in data:
            _validate_principal(db, acl.principal_type.value, str(data["principal_id"]))
        if "permission" in data:
            _validate_permission(data["permission"])
            data["permission"] = ACLPermission(data["permission"])
        if "granted_by" in data:
            _validate_grantor(db, str(data["granted_by"]))
        for key, value in data.items():
            setattr(acl, key, value)
        db.flush()
        db.refresh(acl)
        logger.info("Updated document ACL %s", acl.id)
        return acl

    @staticmethod
    def delete(db: Session, acl_id: str) -> None:
        acl = db.get(DocumentACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Document ACL not found")
        doc_id = acl.document_id
        acl.is_active = False
        db.flush()
        logger.info("Soft-deleted document ACL %s", acl_id)
        publish_event(
            EventType.acl_revoked,
            entity_type="document_acl",
            entity_id=acl_id,
            document_id=doc_id,
        )


# ---------------------------------------------------------------------------
# FolderACLs
# ---------------------------------------------------------------------------


class FolderACLs(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: FolderACLCreate) -> FolderACL:
        if not db.get(Folder, coerce_uuid(payload.folder_id)):
            raise HTTPException(status_code=404, detail="Folder not found")
        _validate_principal(db, payload.principal_type, str(payload.principal_id))
        _validate_permission(payload.permission)
        _validate_grantor(db, str(payload.granted_by))

        data = payload.model_dump()
        data["principal_type"] = PrincipalType(data["principal_type"])
        data["permission"] = ACLPermission(data["permission"])
        acl = FolderACL(**data)
        db.add(acl)
        db.flush()
        db.refresh(acl)
        logger.info("Created folder ACL %s", acl.id)
        publish_event(
            EventType.acl_granted,
            entity_type="folder_acl",
            entity_id=acl.id,
            actor_id=acl.granted_by,
            payload={
                "permission": acl.permission.value,
                "folder_id": str(acl.folder_id),
            },
        )
        return acl

    @staticmethod
    def get(db: Session, acl_id: str) -> FolderACL:
        acl = db.get(FolderACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Folder ACL not found")
        return acl

    @staticmethod
    def list(
        db: Session,
        folder_id: str | None,
        principal_type: str | None,
        principal_id: str | None,
        permission: str | None,
        is_inherited: bool | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[FolderACL]:
        stmt = select(FolderACL)
        if folder_id is not None:
            stmt = stmt.where(FolderACL.folder_id == coerce_uuid(folder_id))
        if principal_type is not None:
            stmt = stmt.where(FolderACL.principal_type == PrincipalType(principal_type))
        if principal_id is not None:
            stmt = stmt.where(FolderACL.principal_id == coerce_uuid(principal_id))
        if permission is not None:
            stmt = stmt.where(FolderACL.permission == ACLPermission(permission))
        if is_inherited is not None:
            stmt = stmt.where(FolderACL.is_inherited == is_inherited)
        if is_active is None:
            stmt = stmt.where(FolderACL.is_active.is_(True))
        else:
            stmt = stmt.where(FolderACL.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {"created_at": FolderACL.created_at},
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(db: Session, acl_id: str, payload: FolderACLUpdate) -> FolderACL:
        acl = db.get(FolderACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Folder ACL not found")
        data = payload.model_dump(exclude_unset=True)
        if "principal_type" in data:
            _validate_principal(
                db,
                data["principal_type"],
                str(data.get("principal_id", acl.principal_id)),
            )
            data["principal_type"] = PrincipalType(data["principal_type"])
        if "principal_id" in data and "principal_type" not in data:
            _validate_principal(db, acl.principal_type.value, str(data["principal_id"]))
        if "permission" in data:
            _validate_permission(data["permission"])
            data["permission"] = ACLPermission(data["permission"])
        if "granted_by" in data:
            _validate_grantor(db, str(data["granted_by"]))
        for key, value in data.items():
            setattr(acl, key, value)
        db.flush()
        db.refresh(acl)
        logger.info("Updated folder ACL %s", acl.id)
        return acl

    @staticmethod
    def delete(db: Session, acl_id: str) -> None:
        acl = db.get(FolderACL, coerce_uuid(acl_id))
        if not acl:
            raise HTTPException(status_code=404, detail="Folder ACL not found")
        acl.is_active = False
        db.flush()
        logger.info("Soft-deleted folder ACL %s", acl_id)
        publish_event(
            EventType.acl_revoked,
            entity_type="folder_acl",
            entity_id=acl_id,
        )


document_acls = DocumentACLs()
folder_acls = FolderACLs()
