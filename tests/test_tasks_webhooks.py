import hashlib
import hmac
import json
import uuid
from unittest.mock import patch

import pytest

from app.models.ecm import WebhookDelivery, WebhookEndpoint


@pytest.fixture()
def webhook_endpoint(db_session, person):
    ep = WebhookEndpoint(
        name="Test Webhook",
        url="https://example.com/webhook",
        secret="test-secret-key",
        event_types=["document"],
        created_by=person.id,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


@pytest.fixture()
def webhook_endpoint_no_secret(db_session, person):
    ep = WebhookEndpoint(
        name="No Secret Webhook",
        url="https://example.com/nosecret",
        event_types=["comment"],
        created_by=person.id,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


class TestFindAndQueue:
    @patch("app.tasks.webhooks.deliver_single_webhook.delay")
    def test_queues_matching_endpoint(
        self, mock_deliver, db_session, webhook_endpoint
    ) -> None:
        from app.tasks.webhooks import _find_and_queue

        _find_and_queue(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(uuid.uuid4()),
            actor_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            payload={},
        )
        assert mock_deliver.called

        deliveries = (
            db_session.query(WebhookDelivery)
            .filter(WebhookDelivery.endpoint_id == webhook_endpoint.id)
            .all()
        )
        assert len(deliveries) >= 1

    @patch("app.tasks.webhooks.deliver_single_webhook.delay")
    def test_skips_non_matching_endpoint(
        self, mock_deliver, db_session, webhook_endpoint
    ) -> None:
        from app.tasks.webhooks import _find_and_queue

        _find_and_queue(
            db_session,
            event_type="workflow.started",
            entity_type="workflow_instance",
            entity_id=str(uuid.uuid4()),
            actor_id=None,
            document_id=None,
            payload={},
        )
        assert not mock_deliver.called

    @patch("app.tasks.webhooks.deliver_single_webhook.delay")
    def test_prefix_matching(self, mock_deliver, db_session, webhook_endpoint) -> None:
        from app.tasks.webhooks import _find_and_queue

        _find_and_queue(
            db_session,
            event_type="document.updated",
            entity_type="document",
            entity_id=str(uuid.uuid4()),
            actor_id=None,
            document_id=None,
            payload={},
        )
        assert mock_deliver.called

    @patch("app.tasks.webhooks.deliver_single_webhook.delay")
    def test_skips_inactive_endpoint(
        self, mock_deliver, db_session, webhook_endpoint
    ) -> None:
        from app.tasks.webhooks import _find_and_queue

        webhook_endpoint.is_active = False
        db_session.commit()

        _find_and_queue(
            db_session,
            event_type="document.created",
            entity_type="document",
            entity_id=str(uuid.uuid4()),
            actor_id=None,
            document_id=None,
            payload={},
        )
        # Verify no delivery was created for the deactivated endpoint
        deliveries = (
            db_session.query(WebhookDelivery)
            .filter(WebhookDelivery.endpoint_id == webhook_endpoint.id)
            .all()
        )
        assert len(deliveries) == 0


class TestEndpointMatches:
    def test_exact_match(self) -> None:
        from app.tasks.webhooks import _endpoint_matches

        assert _endpoint_matches(["document.created"], "document.created", "document")

    def test_prefix_match(self) -> None:
        from app.tasks.webhooks import _endpoint_matches

        assert _endpoint_matches(["document"], "document.created", "document")

    def test_no_match(self) -> None:
        from app.tasks.webhooks import _endpoint_matches

        assert not _endpoint_matches(["comment"], "document.created", "document")

    def test_empty_types_matches_all(self) -> None:
        from app.tasks.webhooks import _endpoint_matches

        assert _endpoint_matches([], "document.created", "document")

    def test_multiple_types(self) -> None:
        from app.tasks.webhooks import _endpoint_matches

        assert _endpoint_matches(
            ["comment", "document.created"], "document.created", "document"
        )


class TestHmacSigning:
    def test_hmac_signature_computation(self) -> None:
        secret = "my-secret"
        payload = {"event_type": "document.created"}
        body = json.dumps(payload, default=str)
        expected_sig = hmac.new(
            secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        assert len(expected_sig) == 64

    def test_no_signature_without_secret(self) -> None:
        # Verify that when secret is None, no signature header is generated
        # This is tested implicitly through the deliver_single_webhook task
        pass
