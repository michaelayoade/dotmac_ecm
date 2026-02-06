import uuid
from unittest.mock import MagicMock, patch

from app.services.event import EventType, publish_event


class TestEventType:
    def test_all_event_types_have_dotted_values(self) -> None:
        for et in EventType:
            assert "." in et.value, f"{et.name} value should contain a dot"

    def test_event_type_count(self) -> None:
        assert len(EventType) == 25

    def test_document_events(self) -> None:
        assert EventType.document_created.value == "document.created"
        assert EventType.document_updated.value == "document.updated"
        assert EventType.document_deleted.value == "document.deleted"
        assert EventType.document_status_changed.value == "document.status_changed"

    def test_version_events(self) -> None:
        assert EventType.version_created.value == "version.created"
        assert EventType.version_deleted.value == "version.deleted"

    def test_checkout_events(self) -> None:
        assert EventType.document_checked_out.value == "document.checked_out"
        assert EventType.document_checked_in.value == "document.checked_in"

    def test_comment_events(self) -> None:
        assert EventType.comment_created.value == "comment.created"
        assert EventType.comment_updated.value == "comment.updated"
        assert EventType.comment_deleted.value == "comment.deleted"

    def test_workflow_events(self) -> None:
        assert EventType.workflow_started.value == "workflow.started"
        assert EventType.workflow_completed.value == "workflow.completed"
        assert EventType.workflow_cancelled.value == "workflow.cancelled"
        assert EventType.workflow_task_created.value == "workflow.task_created"
        assert EventType.workflow_task_completed.value == "workflow.task_completed"

    def test_retention_events(self) -> None:
        assert EventType.retention_applied.value == "retention.applied"
        assert EventType.retention_expired.value == "retention.expired"
        assert EventType.retention_disposed.value == "retention.disposed"

    def test_legal_hold_events(self) -> None:
        assert EventType.legal_hold_created.value == "legal_hold.created"
        assert EventType.legal_hold_released.value == "legal_hold.released"
        assert EventType.legal_hold_document_added.value == "legal_hold.document_added"
        assert (
            EventType.legal_hold_document_removed.value == "legal_hold.document_removed"
        )

    def test_acl_events(self) -> None:
        assert EventType.acl_granted.value == "acl.granted"
        assert EventType.acl_revoked.value == "acl.revoked"


class TestPublishEvent:
    @patch("app.tasks.events.process_event.delay")
    def test_publish_event_calls_delay(self, mock_delay: MagicMock) -> None:
        entity_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        publish_event(
            EventType.document_created,
            entity_type="document",
            entity_id=entity_id,
            actor_id=actor_id,
            document_id=doc_id,
            payload={"key": "value"},
        )
        mock_delay.assert_called_once_with(
            event_type="document.created",
            entity_type="document",
            entity_id=str(entity_id),
            actor_id=str(actor_id),
            document_id=str(doc_id),
            payload={"key": "value"},
        )

    @patch("app.tasks.events.process_event.delay")
    def test_publish_event_none_actor_and_document(self, mock_delay: MagicMock) -> None:
        entity_id = uuid.uuid4()
        publish_event(
            EventType.acl_revoked,
            entity_type="folder_acl",
            entity_id=entity_id,
        )
        mock_delay.assert_called_once_with(
            event_type="acl.revoked",
            entity_type="folder_acl",
            entity_id=str(entity_id),
            actor_id=None,
            document_id=None,
            payload={},
        )

    @patch("app.tasks.events.process_event.delay", side_effect=RuntimeError("down"))
    def test_publish_event_never_raises(self, mock_delay: MagicMock) -> None:
        publish_event(
            EventType.document_created,
            entity_type="document",
            entity_id=uuid.uuid4(),
        )
        # Should not raise


class TestProcessEventTask:
    @patch("app.tasks.search.update_search_index.delay")
    @patch("app.tasks.webhooks.deliver_webhooks.delay")
    @patch("app.tasks.notifications.dispatch_notifications.delay")
    def test_process_event_fans_out(
        self,
        mock_notif_delay: MagicMock,
        mock_webhook_delay: MagicMock,
        mock_search_delay: MagicMock,
    ) -> None:
        from app.tasks.events import process_event

        process_event(
            event_type="document.created",
            entity_type="document",
            entity_id="abc",
            actor_id="actor1",
            document_id="doc1",
            payload={"key": "val"},
        )
        mock_notif_delay.assert_called_once()
        mock_webhook_delay.assert_called_once()
        mock_search_delay.assert_called_once_with(
            document_id="doc1",
            event_type="document.created",
        )

    @patch("app.tasks.search.update_search_index.delay")
    @patch("app.tasks.webhooks.deliver_webhooks.delay")
    @patch(
        "app.tasks.notifications.dispatch_notifications.delay",
        side_effect=RuntimeError("fail"),
    )
    def test_fanout_notifications_failure_does_not_block(
        self,
        mock_notif_delay: MagicMock,
        mock_webhook_delay: MagicMock,
        mock_search_delay: MagicMock,
    ) -> None:
        from app.tasks.events import process_event

        process_event(
            event_type="document.created",
            entity_type="document",
            entity_id="abc",
        )
        mock_webhook_delay.assert_called_once()
        mock_search_delay.assert_called_once()

    @patch("app.tasks.search.update_search_index.delay")
    @patch(
        "app.tasks.webhooks.deliver_webhooks.delay",
        side_effect=RuntimeError("fail"),
    )
    @patch("app.tasks.notifications.dispatch_notifications.delay")
    def test_fanout_webhooks_failure_does_not_block(
        self,
        mock_notif_delay: MagicMock,
        mock_webhook_delay: MagicMock,
        mock_search_delay: MagicMock,
    ) -> None:
        from app.tasks.events import process_event

        process_event(
            event_type="document.created",
            entity_type="document",
            entity_id="abc",
        )
        mock_notif_delay.assert_called_once()
        mock_search_delay.assert_called_once()
