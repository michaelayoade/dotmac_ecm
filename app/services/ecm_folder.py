import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ecm import Folder
from app.models.person import Person
from app.schemas.ecm import FolderCreate, FolderUpdate
from app.services.common import apply_ordering, apply_pagination, coerce_uuid
from app.services.response import ListResponseMixin

logger = logging.getLogger(__name__)


class Folders(ListResponseMixin):
    @staticmethod
    def create(db: Session, payload: FolderCreate) -> Folder:
        creator = db.get(Person, coerce_uuid(payload.created_by))
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")

        if payload.parent_id:
            parent = db.get(Folder, coerce_uuid(payload.parent_id))
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")

        folder = Folder(**payload.model_dump())
        db.add(folder)
        db.flush()

        folder.path = Folders._compute_path(db, folder)
        folder.depth = Folders._compute_depth(folder.path)

        db.flush()
        db.refresh(folder)
        logger.info("Created folder %s", folder.id)
        return folder

    @staticmethod
    def get(db: Session, folder_id: str) -> Folder:
        folder = db.get(Folder, coerce_uuid(folder_id))
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        return folder

    @staticmethod
    def list(
        db: Session,
        parent_id: str | None,
        is_active: bool | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> list[Folder]:
        stmt = select(Folder)
        if parent_id is not None:
            stmt = stmt.where(Folder.parent_id == coerce_uuid(parent_id))
        if is_active is None:
            stmt = stmt.where(Folder.is_active.is_(True))
        else:
            stmt = stmt.where(Folder.is_active == is_active)
        stmt = apply_ordering(
            stmt,
            order_by,
            order_dir,
            {"name": Folder.name, "created_at": Folder.created_at},
        )
        return db.scalars(apply_pagination(stmt, limit, offset)).all()

    @staticmethod
    def update(db: Session, folder_id: str, payload: FolderUpdate) -> Folder:
        folder = db.get(Folder, coerce_uuid(folder_id))
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        data = payload.model_dump(exclude_unset=True)
        old_parent_id = folder.parent_id

        if "parent_id" in data and data["parent_id"] is not None:
            parent = db.get(Folder, coerce_uuid(data["parent_id"]))
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")

        for key, value in data.items():
            setattr(folder, key, value)

        parent_changed = "parent_id" in data and data.get("parent_id") != old_parent_id
        name_changed = "name" in data

        if parent_changed or name_changed:
            old_path = folder.path
            folder.path = Folders._compute_path(db, folder)
            folder.depth = Folders._compute_depth(folder.path)
            if parent_changed:
                Folders._recompute_subtree_paths(db, folder, old_path)

        db.flush()
        db.refresh(folder)
        logger.info("Updated folder %s", folder.id)
        return folder

    @staticmethod
    def delete(db: Session, folder_id: str) -> None:
        folder = db.get(Folder, coerce_uuid(folder_id))
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        folder.is_active = False
        db.flush()
        logger.info("Soft-deleted folder %s", folder.id)

    @staticmethod
    def _compute_path(db: Session, folder: Folder) -> str:
        if folder.parent_id is None:
            return f"/{folder.name}"
        parent = db.get(Folder, folder.parent_id)
        if not parent:
            return f"/{folder.name}"
        return f"{parent.path}/{folder.name}"

    @staticmethod
    def _compute_depth(path: str) -> int:
        return path.count("/") - 1

    @staticmethod
    def _recompute_subtree_paths(db: Session, folder: Folder, old_path: str) -> None:
        descendants = db.scalars(
            select(Folder).where(Folder.path.like(f"{old_path}/%"))
        ).all()
        for child in descendants:
            child.path = folder.path + child.path[len(old_path) :]
            child.depth = Folders._compute_depth(child.path)


folders = Folders()
