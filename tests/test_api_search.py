class TestSearchEndpoints:
    def test_search_basic(self, client, auth_headers, document) -> None:
        resp = client.get(
            f"/search?q={document.title[:8]}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1

    def test_search_empty_query(self, client, auth_headers, document) -> None:
        resp = client.get("/search?q=", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_search_no_results(self, client, auth_headers) -> None:
        resp = client.get("/search?q=nonexistent_xyz_12345", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_search_with_folder_filter(
        self, client, auth_headers, document, folder
    ) -> None:
        resp = client.get(f"/search?q=&folder_id={folder.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_search_with_status_filter(self, client, auth_headers, document) -> None:
        resp = client.get("/search?q=&status=draft", headers=auth_headers)
        assert resp.status_code == 200

    def test_search_pagination(self, client, auth_headers, document) -> None:
        resp = client.get("/search?q=&limit=1&offset=0", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["items"]) <= 1

    def test_search_v1_prefix(self, client, auth_headers, document) -> None:
        resp = client.get("/api/v1/search?q=", headers=auth_headers)
        assert resp.status_code == 200

    def test_search_with_classification_filter(
        self, client, auth_headers, document
    ) -> None:
        resp = client.get("/search?q=&classification=internal", headers=auth_headers)
        assert resp.status_code == 200
