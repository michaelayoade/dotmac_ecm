import uuid

from app.models.ecm import Folder


def _create_folder(db_session, person, name="Test Folder", parent_id=None):
    folder = Folder(
        name=name,
        created_by=person.id,
        parent_id=parent_id,
        path=f"/{name}",
        depth=0,
    )
    db_session.add(folder)
    db_session.commit()
    db_session.refresh(folder)
    return folder


class TestFolderEndpoints:
    def test_create_folder(self, client, auth_headers, person):
        resp = client.post(
            "/ecm/folders",
            json={"name": "New Folder", "created_by": str(person.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Folder"
        assert data["path"] == "/New Folder"

    def test_get_folder(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        resp = client.get(f"/ecm/folders/{folder.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(folder.id)

    def test_get_folder_not_found(self, client, auth_headers):
        resp = client.get(f"/ecm/folders/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_folders(self, client, auth_headers, db_session, person):
        _create_folder(db_session, person, name=f"F_{uuid.uuid4().hex[:6]}")
        resp = client.get("/ecm/folders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "count" in data

    def test_update_folder(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        resp = client.patch(
            f"/ecm/folders/{folder.id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_delete_folder(self, client, auth_headers, db_session, person):
        folder = _create_folder(db_session, person)
        resp = client.delete(f"/ecm/folders/{folder.id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_unauthenticated_request(self, client):
        resp = client.get("/ecm/folders")
        assert resp.status_code in (401, 403)
