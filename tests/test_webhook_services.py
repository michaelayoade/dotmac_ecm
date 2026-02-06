import uuid

import pytest
from fastapi import HTTPException

from app.models.ecm import WebhookDelivery, WebhookDeliveryStatus, WebhookEndpoint
from app.schemas.webhook import WebhookEndpointCreate, WebhookEndpointUpdate


@pytest.fixture()
def webhook_endpoint(db_session, person):
    ep = WebhookEndpoint(
        name="Test Webhook",
        url="https://example.com/webhook",
        secret="test-secret",
        event_types=["document.created", "document.updated"],
        created_by=person.id,
    )
    db_session.add(ep)
    db_session.commit()
    db_session.refresh(ep)
    return ep


@pytest.fixture()
def webhook_delivery(db_session, webhook_endpoint):
    d = WebhookDelivery(
        endpoint_id=webhook_endpoint.id,
        event_type="document.created",
        payload={"event_type": "document.created"},
        status=WebhookDeliveryStatus.pending,
    )
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    return d


class TestWebhookEndpointsService:
    def test_create(self, db_session, person) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointCreate(
            name="My Webhook",
            url="https://example.com/hook",
            secret="secret123",
            event_types=["document"],
            created_by=person.id,
        )
        result = webhook_endpoints.create(db_session, payload)
        assert result.name == "My Webhook"
        assert result.url == "https://example.com/hook"
        assert result.event_types == ["document"]

    def test_create_creator_not_found(self, db_session) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointCreate(
            name="My Webhook",
            url="https://example.com/hook",
            event_types=["document"],
            created_by=uuid.uuid4(),
        )
        with pytest.raises(HTTPException) as exc:
            webhook_endpoints.create(db_session, payload)
        assert exc.value.status_code == 404

    def test_get(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        result = webhook_endpoints.get(db_session, str(webhook_endpoint.id))
        assert result.id == webhook_endpoint.id

    def test_get_not_found(self, db_session) -> None:
        from app.services.webhook import webhook_endpoints

        with pytest.raises(HTTPException) as exc:
            webhook_endpoints.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        result = webhook_endpoints.list(
            db_session,
            created_by=str(webhook_endpoint.created_by),
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) >= 1

    def test_list_filter_by_creator(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        result = webhook_endpoints.list(
            db_session,
            created_by=str(webhook_endpoint.created_by),
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert all(
            str(ep.created_by) == str(webhook_endpoint.created_by) for ep in result
        )

    def test_update(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointUpdate(name="Updated Name")
        result = webhook_endpoints.update(db_session, str(webhook_endpoint.id), payload)
        assert result.name == "Updated Name"

    def test_update_not_found(self, db_session) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointUpdate(name="Updated")
        with pytest.raises(HTTPException) as exc:
            webhook_endpoints.update(db_session, str(uuid.uuid4()), payload)
        assert exc.value.status_code == 404

    def test_delete(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        webhook_endpoints.delete(db_session, str(webhook_endpoint.id))
        ep = db_session.get(WebhookEndpoint, webhook_endpoint.id)
        assert ep.is_active is False

    def test_delete_not_found(self, db_session) -> None:
        from app.services.webhook import webhook_endpoints

        with pytest.raises(HTTPException) as exc:
            webhook_endpoints.delete(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_create_without_secret(self, db_session, person) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointCreate(
            name="No Secret",
            url="https://example.com/hook2",
            event_types=["comment"],
            created_by=person.id,
        )
        result = webhook_endpoints.create(db_session, payload)
        assert result.secret is None

    def test_update_event_types(self, db_session, webhook_endpoint) -> None:
        from app.services.webhook import webhook_endpoints

        payload = WebhookEndpointUpdate(event_types=["workflow"])
        result = webhook_endpoints.update(db_session, str(webhook_endpoint.id), payload)
        assert result.event_types == ["workflow"]


class TestWebhookDeliveriesService:
    def test_get(self, db_session, webhook_delivery) -> None:
        from app.services.webhook import webhook_deliveries

        result = webhook_deliveries.get(db_session, str(webhook_delivery.id))
        assert result.id == webhook_delivery.id

    def test_get_not_found(self, db_session) -> None:
        from app.services.webhook import webhook_deliveries

        with pytest.raises(HTTPException) as exc:
            webhook_deliveries.get(db_session, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_list(self, db_session, webhook_delivery) -> None:
        from app.services.webhook import webhook_deliveries

        result = webhook_deliveries.list(
            db_session,
            endpoint_id=str(webhook_delivery.endpoint_id),
            event_type=None,
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert len(result) >= 1

    def test_list_filter_by_status(self, db_session, webhook_delivery) -> None:
        from app.services.webhook import webhook_deliveries

        result = webhook_deliveries.list(
            db_session,
            endpoint_id=None,
            event_type=None,
            status="pending",
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert all(d.status == WebhookDeliveryStatus.pending for d in result)

    def test_list_filter_by_event_type(self, db_session, webhook_delivery) -> None:
        from app.services.webhook import webhook_deliveries

        result = webhook_deliveries.list(
            db_session,
            endpoint_id=None,
            event_type="document.created",
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert all(d.event_type == "document.created" for d in result)

    def test_list_filter_by_endpoint(self, db_session, webhook_delivery) -> None:
        from app.services.webhook import webhook_deliveries

        result = webhook_deliveries.list(
            db_session,
            endpoint_id=str(webhook_delivery.endpoint_id),
            event_type=None,
            status=None,
            is_active=None,
            order_by="created_at",
            order_dir="desc",
            limit=25,
            offset=0,
        )
        assert all(
            str(d.endpoint_id) == str(webhook_delivery.endpoint_id) for d in result
        )
