from datetime import UTC, datetime
from uuid import uuid4

from httpx import AsyncClient


async def create_location(
    client: AsyncClient,
    name: str,
    *,
    latitude: float = -33.8688,
    longitude: float = 151.2093,
) -> str:
    buyer_response = await client.post(
        "/api/buyers",
        json={"name": f"Buyer for {name}"},
    )
    assert buyer_response.status_code == 201
    buyer_id = buyer_response.json()["id"]

    location_response = await client.post(
        "/api/locations",
        json={
            "name": name,
            "buyer_id": buyer_id,
            "latitude": latitude,
            "longitude": longitude,
        },
    )
    assert location_response.status_code == 201
    return location_response.json()["id"]


async def create_price(
    client: AsyncClient,
    location_id: str,
    commodity: str,
    price_per_tonne: str = "350.50",
) -> dict[str, object]:
    response = await client.post(
        "/api/prices",
        json={
            "location_id": location_id,
            "commodity": commodity,
            "price_per_tonne": price_per_tonne,
            "effective_date": datetime(2026, 11, 2, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_create_price_success(client: AsyncClient) -> None:
    location_id = await create_location(client, "Wheat receival")

    response = await client.post(
        "/api/prices",
        json={
            "location_id": location_id,
            "commodity": "Wheat",
            "price_per_tonne": "350.50",
            "effective_date": datetime(2026, 11, 2, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["location_id"] == location_id
    assert body["commodity"] == "Wheat"
    assert body["price_per_tonne"] == "350.50"
    assert datetime.fromisoformat(body["effective_date"].replace("Z", "+00:00")) == datetime(
        2026, 11, 2, tzinfo=UTC
    )
    assert body["created_at"]
    assert body["updated_at"]


async def test_list_and_filter_prices(client: AsyncClient) -> None:
    first_location = await create_location(client, "First receival")
    second_location = await create_location(client, "Second receival")
    wheat_first = await create_price(client, first_location, "Wheat")
    barley_first = await create_price(client, first_location, "Barley", "290.00")
    wheat_second = await create_price(client, second_location, "Wheat", "355.00")

    commodity_response = await client.get("/api/prices", params={"commodity": "Wheat"})
    location_response = await client.get(
        "/api/prices", params={"location_id": first_location}
    )

    assert commodity_response.status_code == 200
    assert {item["id"] for item in commodity_response.json()} == {
        wheat_first["id"],
        wheat_second["id"],
    }
    assert location_response.status_code == 200
    assert {item["id"] for item in location_response.json()} == {
        wheat_first["id"],
        barley_first["id"],
    }


async def test_get_price_by_id(client: AsyncClient) -> None:
    location_id = await create_location(client, "Get-by-ID receival")
    created = await create_price(client, location_id, "Canola")

    response = await client.get(f"/api/prices/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


async def test_update_price(client: AsyncClient) -> None:
    location_id = await create_location(client, "Update receival")
    created = await create_price(client, location_id, "Wheat")

    response = await client.put(
        f"/api/prices/{created['id']}",
        json={
            "location_id": location_id,
            "commodity": "Wheat",
            "price_per_tonne": "375.25",
            "effective_date": datetime(2026, 11, 2, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["price_per_tonne"] == "375.25"


async def test_delete_price(client: AsyncClient) -> None:
    location_id = await create_location(client, "Delete receival")
    created = await create_price(client, location_id, "Wheat")

    delete_response = await client.delete(f"/api/prices/{created['id']}")
    get_response = await client.get(f"/api/prices/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


async def test_create_price_validation_errors(client: AsyncClient) -> None:
    location_id = await create_location(client, "Validation receival")
    valid_payload: dict[str, object] = {
        "location_id": location_id,
        "commodity": "Wheat",
        "price_per_tonne": "350.50",
        "effective_date": datetime(2026, 11, 2, tzinfo=UTC).isoformat(),
    }
    invalid_payloads = [
        {**valid_payload, "price_per_tonne": "0"},
        {**valid_payload, "price_per_tonne": "-1"},
        {"location_id": location_id, "commodity": "Wheat", "price_per_tonne": "350.50"},
        {},
    ]

    for payload in invalid_payloads:
        response = await client.post("/api/prices", json=payload)
        assert response.status_code in {400, 422}


async def test_price_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/api/prices/{uuid4()}")

    assert response.status_code == 404


async def test_nearby_locations_include_buyers_and_respect_pagination(
    client: AsyncClient,
) -> None:
    first_location = await create_location(client, "Nearby first")
    second_location = await create_location(client, "Nearby second")
    other_commodity_location = await create_location(client, "Nearby barley")
    distant_location = await create_location(
        client, "Distant wheat", latitude=-27.4698, longitude=153.0251
    )
    await create_price(client, first_location, "Wheat")
    await create_price(client, second_location, "Wheat")
    await create_price(client, other_commodity_location, "Barley")
    await create_price(client, distant_location, "Wheat")

    first_page = await client.get(
        "/api/locations/nearby",
        params={
            "lat": -33.8688,
            "lon": 151.2093,
            "radius_km": 10,
            "commodity": "Wheat",
            "limit": 1,
        },
    )
    second_page = await client.get(
        "/api/locations/nearby",
        params={
            "lat": -33.8688,
            "lon": 151.2093,
            "radius_km": 10,
            "commodity": "Wheat",
            "limit": 1,
            "offset": 1,
        },
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]
    for location in (*first_page.json(), *second_page.json()):
        assert location["buyer"]["name"].startswith("Buyer for Nearby")
        assert [price["commodity"] for price in location["prices"]] == ["Wheat"]


async def test_nearby_rejects_radius_above_ceiling(client: AsyncClient) -> None:
    response = await client.get(
        "/api/locations/nearby",
        params={"lat": 0, "lon": 0, "radius_km": 500.1},
    )

    assert response.status_code == 422


async def test_buyer_crud(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/buyers",
        json={"name": "Buyer CRUD", "email": "buyer@example.test", "phone": "0400000000"},
    )
    buyer_id = create_response.json()["id"]

    read_response = await client.get(f"/api/buyers/{buyer_id}")
    list_response = await client.get("/api/buyers")
    update_response = await client.put(
        f"/api/buyers/{buyer_id}",
        json={"name": "Updated Buyer", "email": "updated@example.test", "phone": None},
    )
    delete_response = await client.delete(f"/api/buyers/{buyer_id}")
    missing_response = await client.get(f"/api/buyers/{buyer_id}")

    assert create_response.status_code == 201
    assert read_response.status_code == 200
    assert any(item["id"] == buyer_id for item in list_response.json())
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Buyer"
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


async def test_location_crud(client: AsyncClient) -> None:
    buyer_response = await client.post("/api/buyers", json={"name": "Location CRUD buyer"})
    buyer_id = buyer_response.json()["id"]
    create_response = await client.post(
        "/api/locations",
        json={
            "name": "Location CRUD",
            "buyer_id": buyer_id,
            "latitude": -33.8688,
            "longitude": 151.2093,
        },
    )
    location_id = create_response.json()["id"]

    read_response = await client.get(f"/api/locations/{location_id}")
    list_response = await client.get("/api/locations")
    update_response = await client.put(
        f"/api/locations/{location_id}",
        json={
            "name": "Updated Location",
            "buyer_id": buyer_id,
            "latitude": -34.0,
            "longitude": 150.0,
        },
    )
    delete_response = await client.delete(f"/api/locations/{location_id}")
    missing_response = await client.get(f"/api/locations/{location_id}")

    assert create_response.status_code == 201
    assert read_response.status_code == 200
    assert any(item["id"] == location_id for item in list_response.json())
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Location"
    assert update_response.json()["latitude"] == -34.0
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404
