from collections.abc import Generator

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.common import ListResponse
from app.schemas.ecm import FolderCreate, FolderRead, FolderUpdate
from app.services import ecm_folder as folder_service

router = APIRouter(prefix="/ecm/folders", tags=["ecm-folders"])


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


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(payload: FolderCreate, db: Session = Depends(get_db)) -> FolderRead:
    return folder_service.folders.create(db, payload)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(folder_id: str, db: Session = Depends(get_db)) -> FolderRead:
    return folder_service.folders.get(db, folder_id)


@router.get("", response_model=ListResponse[FolderRead])
def list_folders(
    parent_id: str | None = None,
    is_active: bool | None = None,
    order_by: str = Query(default="name"),
    order_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return folder_service.folders.list_response(
        db, parent_id, is_active, order_by, order_dir, limit, offset
    )


@router.patch("/{folder_id}", response_model=FolderRead)
def update_folder(
    folder_id: str, payload: FolderUpdate, db: Session = Depends(get_db)
) -> FolderRead:
    return folder_service.folders.update(db, folder_id, payload)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: str, db: Session = Depends(get_db)) -> None:
    folder_service.folders.delete(db, folder_id)
