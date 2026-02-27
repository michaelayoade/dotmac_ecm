import uuid

import pytest

from app.models.ecm import WebhookDelivery, WebhookDeliveryStatus, WebhookEndpoint


@pytest.fixture()
def webhook_endpoint(db_session, person):
    ep = WebhookEndpoint(
        name="Test Webhook",
        url=f"https://example.com/webhook/{uuid.uuid4().hex[:8]}",
        secret="test-secret",
        event_types=["document.created"],
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


class TestWebhookEndpointEndpoints:
    def test_create(self, client, auth_headers, person) -> None:
        resp = client.post(
            "/webhooks/endpoints",
            json={
                "name": "My Hook",
                "url": f"https://example.com/{uuid.uuid4().hex[:8]}",
                "event_types": ["document"],
                "created_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Hook"

    @pytest.mark.parametrize(
        "bad_url",
        [
            "ftp://example.com/hook",
            "http://127.0.0.1/hook",
            "http://[::1]/hook",
            "http://169.254.169.254/hook",
            "http://10.0.0.1/hook",
            "http://172.16.1.1/hook",
            "http://192.168.1.1/hook",
        ],
    )
    def test_create_rejects_ssrf_targets(
        self, client, auth_headers, person, bad_url: str
    ) -> None:
        resp = client.post(
            "/webhooks/endpoints",
            json={
                "name": "Blocked Hook",
                "url": bad_url,
                "event_types": ["document"],
                "created_by": str(person.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_get(self, client, auth_headers, webhook_endpoint) -> None:
        resp = client.get(
            f"/webhooks/endpoints/{webhook_endpoint.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(webhook_endpoint.id)

    def test_get_not_found(self, client, auth_headers) -> None:
        resp = client.get(f"/webhooks/endpoints/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list(self, client, auth_headers, webhook_endpoint) -> None:
        resp = client.get("/webhooks/endpoints", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_update(self, client, auth_headers, webhook_endpoint) -> None:
        resp = client.patch(
            f"/webhooks/endpoints/{webhook_endpoint.id}",
            json={"name": "Updated Hook"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Hook"

    @pytest.mark.parametrize(
        "bad_url",
        [
            "ftp://example.com/hook",
            "http://127.0.0.1/hook",
            "http://[::1]/hook",
            "http://169.254.169.254/hook",
            "http://10.0.0.1/hook",
            "http://172.16.1.1/hook",
            "http://192.168.1.1/hook",
        ],
    )
    def test_update_rejects_ssrf_targets(
        self, client, auth_headers, webhook_endpoint, bad_url: str
    ) -> None:
        resp = client.patch(
            f"/webhooks/endpoints/{webhook_endpoint.id}",
            json={"url": bad_url},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_delete(self, client, auth_headers, webhook_endpoint) -> None:
        resp = client.delete(
            f"/webhooks/endpoints/{webhook_endpoint.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    def test_list_filter_by_creator(
        self, client, auth_headers, person, webhook_endpoint
    ) -> None:
        resp = client.get(
            f"/webhooks/endpoints?created_by={person.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["created_by"] == str(person.id)


class TestWebhookDeliveryEndpoints:
    def test_list_deliveries(self, client, auth_headers, webhook_delivery) -> None:
        resp = client.get("/webhooks/deliveries", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_get_delivery(self, client, auth_headers, webhook_delivery) -> None:
        resp = client.get(
            f"/webhooks/deliveries/{webhook_delivery.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(webhook_delivery.id)

    def test_get_delivery_not_found(self, client, auth_headers) -> None:
        resp = client.get(f"/webhooks/deliveries/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_filter_by_endpoint(
        self, client, auth_headers, webhook_delivery
    ) -> None:
        resp = client.get(
            f"/webhooks/deliveries?endpoint_id={webhook_delivery.endpoint_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["endpoint_id"] == str(webhook_delivery.endpoint_id)

    def test_list_filter_by_status(
        self, client, auth_headers, webhook_delivery
    ) -> None:
        resp = client.get("/webhooks/deliveries?status=pending", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "pending"

    def test_v1_prefix(self, client, auth_headers, webhook_endpoint) -> None:
        resp = client.get(
            f"/api/v1/webhooks/endpoints/{webhook_endpoint.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
