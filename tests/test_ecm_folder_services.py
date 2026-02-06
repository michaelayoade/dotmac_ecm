import uuid

import pytest
from fastapi import HTTPException

from app.schemas.ecm import FolderCreate, FolderUpdate
from app.services.ecm_folder import Folders


class TestFoldersCreate:
    def test_create_root_folder(self, db_session, person):
        payload = FolderCreate(
            name="Root Folder",
            description="A root folder",
            created_by=person.id,
        )
        folder = Folders.create(db_session, payload)
        assert folder.name == "Root Folder"
        assert folder.parent_id is None
        assert folder.path == "/Root Folder"
        assert folder.depth == 0
        assert folder.is_active is True

    def test_create_child_folder(self, db_session, person):
        parent = FolderCreate(name="Parent", created_by=person.id)
        parent_folder = Folders.create(db_session, parent)

        child = FolderCreate(
            name="Child", created_by=person.id, parent_id=parent_folder.id
        )
        child_folder = Folders.create(db_session, child)
        assert child_folder.path == "/Parent/Child"
        assert child_folder.depth == 1

    def test_create_folder_invalid_creator(self, db_session):
        payload = FolderCreate(name="Bad", created_by=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            Folders.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Creator" in exc.value.detail

    def test_create_folder_invalid_parent(self, db_session, person):
        payload = FolderCreate(name="Bad", created_by=person.id, parent_id=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            Folders.create(db_session, payload)
        assert exc.value.status_code == 404
        assert "Parent" in exc.value.detail


class TestFoldersGet:
    def test_get_folder(self, db_session, person):
        payload = FolderCreate(name="GetMe", created_by=person.id)
        created = Folders.create(db_session, payload)
        found = Folders.get(db_session, str(created.id))
        assert found.id == created.id

    def test_get_folder_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Folders.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestFoldersList:
    def test_list_folders_by_parent(self, db_session, person):
        root = Folders.create(
            db_session,
            FolderCreate(name=f"root_{uuid.uuid4().hex[:6]}", created_by=person.id),
        )
        Folders.create(
            db_session,
            FolderCreate(name="child1", created_by=person.id, parent_id=root.id),
        )
        Folders.create(
            db_session,
            FolderCreate(name="child2", created_by=person.id, parent_id=root.id),
        )
        children = Folders.list(
            db_session,
            parent_id=str(root.id),
            is_active=None,
            order_by="name",
            order_dir="asc",
            limit=50,
            offset=0,
        )
        assert len(children) >= 2


class TestFoldersUpdate:
    def test_update_folder_name(self, db_session, person):
        folder = Folders.create(
            db_session, FolderCreate(name="OldName", created_by=person.id)
        )
        updated = Folders.update(
            db_session, str(folder.id), FolderUpdate(name="NewName")
        )
        assert updated.name == "NewName"
        assert updated.path == "/NewName"

    def test_update_move_folder_recomputes_subtree(self, db_session, person):
        a = Folders.create(db_session, FolderCreate(name="A", created_by=person.id))
        b = Folders.create(
            db_session,
            FolderCreate(name="B", created_by=person.id, parent_id=a.id),
        )
        c = Folders.create(
            db_session,
            FolderCreate(name="C", created_by=person.id, parent_id=b.id),
        )
        new_root = Folders.create(
            db_session, FolderCreate(name="NewRoot", created_by=person.id)
        )
        Folders.update(db_session, str(b.id), FolderUpdate(parent_id=new_root.id))
        db_session.refresh(c)
        assert c.path == "/NewRoot/B/C"
        assert c.depth == 2

    def test_update_folder_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Folders.update(db_session, str(uuid.uuid4()), FolderUpdate(name="X"))
        assert exc.value.status_code == 404


class TestFoldersDelete:
    def test_soft_delete_folder(self, db_session, person):
        folder = Folders.create(
            db_session, FolderCreate(name="ToDelete", created_by=person.id)
        )
        Folders.delete(db_session, str(folder.id))
        db_session.refresh(folder)
        assert folder.is_active is False

    def test_delete_folder_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc:
            Folders.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404
