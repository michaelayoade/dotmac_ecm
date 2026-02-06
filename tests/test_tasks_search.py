import uuid
from unittest.mock import MagicMock, patch


class TestUpdateSearchIndex:
    @patch("app.db.SessionLocal")
    @patch("app.services.search.SearchService.update_document_vector")
    def test_calls_update_document_vector(self, mock_update, mock_session_cls) -> None:
        from app.tasks.search import update_search_index

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        doc_id = str(uuid.uuid4())
        update_search_index(document_id=doc_id, event_type="document.created")

        mock_update.assert_called_once_with(mock_db, doc_id)
        mock_db.close.assert_called_once()

    def test_skips_when_no_document_id(self) -> None:
        from app.tasks.search import update_search_index

        # Should return early without opening a session
        with patch("app.db.SessionLocal") as mock_session_cls:
            update_search_index(document_id=None, event_type="document.created")
            mock_session_cls.assert_not_called()

    @patch("app.db.SessionLocal")
    @patch("app.services.search.SearchService.update_document_vector")
    def test_handles_exception_gracefully(self, mock_update, mock_session_cls) -> None:
        from app.tasks.search import update_search_index

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_update.side_effect = Exception("fail")

        # Should not raise
        update_search_index(
            document_id=str(uuid.uuid4()), event_type="document.created"
        )
        mock_db.close.assert_called_once()


class TestReindexAllDocuments:
    @patch("app.db.SessionLocal")
    @patch("app.services.search.SearchService.update_document_vector")
    def test_reindexes_active_documents(self, mock_update, mock_session_cls) -> None:
        from app.tasks.search import reindex_all_documents

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        doc1 = MagicMock()
        doc1.id = uuid.uuid4()
        doc2 = MagicMock()
        doc2.id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.all.return_value = [doc1, doc2]

        reindex_all_documents()

        assert mock_update.call_count == 2
        mock_db.close.assert_called_once()

    @patch("app.db.SessionLocal")
    @patch("app.services.search.SearchService.update_document_vector")
    def test_handles_per_document_failure(self, mock_update, mock_session_cls) -> None:
        from app.tasks.search import reindex_all_documents

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        doc1 = MagicMock()
        doc1.id = uuid.uuid4()
        doc2 = MagicMock()
        doc2.id = uuid.uuid4()
        mock_db.query.return_value.filter.return_value.all.return_value = [doc1, doc2]

        # First doc fails, second succeeds
        mock_update.side_effect = [
            Exception("fail"),
            None,
        ]

        # Should not raise
        reindex_all_documents()
        assert mock_update.call_count == 2
        mock_db.close.assert_called_once()
