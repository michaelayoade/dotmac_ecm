import uuid


from app.models.ecm import Document


class TestSearchService:
    def test_search_by_title(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q=document.title[:10])
        assert len(results) >= 1
        assert any(d.id == document.id for d in results)

    def test_search_by_file_name(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="test.pdf")
        assert len(results) >= 1

    def test_search_empty_query_returns_all_active(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="")
        assert len(results) >= 1

    def test_search_no_results(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="nonexistent_xyz_abc")
        assert len(results) == 0

    def test_search_filter_by_folder(self, db_session, document, folder) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="", folder_id=str(folder.id))
        assert all(str(d.folder_id) == str(folder.id) for d in results)

    def test_search_filter_by_status(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="", status="draft")
        assert all(d.status.value == "draft" for d in results)

    def test_search_filter_by_classification(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="", classification="internal")
        assert all(d.classification.value == "internal" for d in results)

    def test_search_excludes_inactive(self, db_session, person, folder) -> None:
        from app.services.search import SearchService

        doc = Document(
            title="inactive_search_test",
            file_name="inactive.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
            folder_id=folder.id,
            is_active=False,
        )
        db_session.add(doc)
        db_session.commit()

        results = SearchService.search(db_session, q="inactive_search_test")
        assert len(results) == 0

    def test_search_pagination(self, db_session, document) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="", limit=1, offset=0)
        assert len(results) <= 1

    def test_search_description_match(self, db_session, person, folder) -> None:
        from app.services.search import SearchService

        doc = Document(
            title="desc_test_doc",
            description="unique_description_search_test_xyz",
            file_name="desc_test.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
            folder_id=folder.id,
        )
        db_session.add(doc)
        db_session.commit()

        results = SearchService.search(
            db_session, q="unique_description_search_test_xyz"
        )
        assert len(results) == 1

    def test_update_document_vector_noop_on_sqlite(self, db_session, document) -> None:
        from app.services.search import SearchService

        # Should not raise on SQLite
        SearchService.update_document_vector(db_session, str(document.id))

    def test_update_document_vector_missing_doc(self, db_session) -> None:
        from app.services.search import SearchService

        SearchService.update_document_vector(db_session, str(uuid.uuid4()))

    def test_search_filter_by_created_by(self, db_session, document, person) -> None:
        from app.services.search import SearchService

        results = SearchService.search(db_session, q="", created_by=str(person.id))
        assert all(str(d.created_by) == str(person.id) for d in results)

    def test_search_case_insensitive(self, db_session, person, folder) -> None:
        from app.services.search import SearchService

        doc = Document(
            title="CaseTestDocument",
            file_name="case.pdf",
            file_size=100,
            mime_type="application/pdf",
            created_by=person.id,
            folder_id=folder.id,
        )
        db_session.add(doc)
        db_session.commit()

        results = SearchService.search(db_session, q="casetestdocument")
        assert len(results) >= 1
