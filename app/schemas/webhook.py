from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


_DISALLOWED_IPV4_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_IPV6_LOOPBACK = ipaddress.ip_address("::1")


def _validate_webhook_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Webhook URL must use http or https")
    if not parsed.hostname:
        raise ValueError("Webhook URL must include a host")

    try:
        target_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return value

    if isinstance(target_ip, ipaddress.IPv4Address) and any(
        target_ip in network for network in _DISALLOWED_IPV4_NETWORKS
    ):
        raise ValueError("Webhook URL host cannot be loopback, link-local, or private")
    if target_ip == _IPV6_LOOPBACK:
        raise ValueError("Webhook URL host cannot be loopback, link-local, or private")
    return value


class WebhookEndpointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    secret: str | None = Field(default=None, max_length=255)
    event_types: list[str]
    created_by: UUID

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_webhook_url(value)


class WebhookEndpointUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    secret: str | None = Field(default=None, max_length=255)
    event_types: list[str] | None = None
    is_active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_webhook_url(value)


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    secret: str | None = None
    event_types: list[str]
    created_by: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint_id: UUID
    event_type: str
    payload: dict[str, Any]
    status: str
    response_status_code: int | None = None
    response_body: str | None = None
    attempts: int
    last_attempt_at: datetime | None = None
    is_active: bool
    created_at: datetime
