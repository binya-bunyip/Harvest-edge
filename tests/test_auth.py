from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from harvest_edge.config import get_settings

ApiKeyFactory = Callable[..., Awaitable[str]]

async def test_valid_api_key_authorizes_write(client: AsyncClient) -> None:
    response = await client.post("/api/buyers", json={"name": "Authorized buyer"})

    assert response.status_code == 201


async def test_missing_and_invalid_api_keys_are_unauthorized(client: AsyncClient) -> None:
    client.headers.pop("X-API-Key")
    missing_response = await client.post("/api/buyers", json={"name": "Missing key"})
    invalid_response = await client.post(
        "/api/buyers",
        json={"name": "Invalid key"},
        headers={"X-API-Key": "he_live_not-a-valid-key"},
    )

    assert missing_response.status_code == 401
    assert invalid_response.status_code == 401


async def test_insufficient_scopes_are_forbidden(
    client: AsyncClient, api_key_factory: ApiKeyFactory
) -> None:
    read_only_key = await api_key_factory(scopes=["read:prices"])
    response = await client.post(
        "/api/prices",
        json={},
        headers={"X-API-Key": read_only_key},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("is_active", "expires_at"),
    [
        (False, None),
        (True, datetime.now(UTC) - timedelta(minutes=1)),
    ],
)
async def test_inactive_or_expired_api_keys_are_unauthorized(
    client: AsyncClient,
    api_key_factory: ApiKeyFactory,
    is_active: bool,
    expires_at: datetime | None,
) -> None:
    raw_key = await api_key_factory(is_active=is_active, expires_at=expires_at)
    response = await client.post(
        "/api/buyers",
        json={"name": "Rejected key"},
        headers={"X-API-Key": raw_key},
    )

    assert response.status_code == 401


async def test_bearer_jwt_authorizes_scoped_request(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "test-jwt-secret-that-is-long-enough"
    monkeypatch.setattr(get_settings(), "jwt_secret_key", SecretStr(secret))
    token = jwt.encode(
        {
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "scope": "write:prices",
            "buyer_id": 42,
        },
        secret,
        algorithm="HS256",
    )
    client.headers.pop("X-API-Key")
    response = await client.post(
        "/api/buyers",
        json={"name": "Bearer buyer"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201


async def test_expired_bearer_jwt_is_unauthorized(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "test-jwt-secret-that-is-long-enough"
    monkeypatch.setattr(get_settings(), "jwt_secret_key", SecretStr(secret))
    token = jwt.encode(
        {
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "scope": "write:prices",
        },
        secret,
        algorithm="HS256",
    )
    client.headers.pop("X-API-Key")
    response = await client.post(
        "/api/buyers",
        json={"name": "Expired bearer"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


async def test_admin_can_create_an_api_key_once(client: AsyncClient) -> None:
    response = await client.post(
        "/api/admin/keys",
        json={"name": "New integration key", "scopes": ["write:prices"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["api_key"].startswith("he_live_")
    assert body["key_prefix"] == body["api_key"][:8]
    assert "key_hash" not in body
    authorized = await client.post(
        "/api/buyers",
        json={"name": "Created key buyer"},
        headers={"X-API-Key": body["api_key"]},
    )
    assert authorized.status_code == 201
