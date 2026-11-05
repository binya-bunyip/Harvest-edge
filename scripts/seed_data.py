import argparse
import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import httpx

BUYERS = (
    {
        "name": "AgriCorp",
        "email": "market-data@agricorp.example",
        "phone": "+61 2 5550 0100",
    },
    {
        "name": "Southern Grain Exchange",
        "email": "market-data@southerngrain.example",
        "phone": "+61 3 5550 0200",
    },
)

LOCATIONS = (
    {
        "name": "AgriCorp Wagga Wagga",
        "buyer_name": "AgriCorp",
        "latitude": -35.1082,
        "longitude": 147.3598,
        "prices": {"Wheat": "350.50", "Canola": "612.00"},
    },
    {
        "name": "Southern Grain Exchange Geelong",
        "buyer_name": "Southern Grain Exchange",
        "latitude": -38.1499,
        "longitude": 144.3617,
        "prices": {"Barley": "285.75"},
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed mock buyers, locations, and grain prices.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("HARVEST_EDGE_API_URL", "http://127.0.0.1:8000"),
        help="Harvest Edge API origin (default: HARVEST_EDGE_API_URL or localhost:8000)",
    )
    parser.add_argument(
        "--radius-km",
        type=float,
        default=10.0,
        help="Radius used to verify each seeded location (maximum 500 km)",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if not 0 < args.radius_km <= 500:
        parser.error("--radius-km must be greater than 0 and at most 500")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    return args


async def checked_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    expected_status: int,
    **kwargs: Any,
) -> Any:
    response = await client.request(method, path, **kwargs)
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {path} returned {response.status_code}; "
            f"expected {expected_status}: {response.text}"
        )
    return response.json() if response.content else None


async def get_or_create_buyer(
    client: httpx.AsyncClient, buyer_data: dict[str, str]
) -> dict[str, Any]:
    buyers = await checked_request(
        client, "GET", "/api/buyers", expected_status=200, params={"limit": 500}
    )
    for buyer in buyers:
        if buyer["name"] == buyer_data["name"]:
            return buyer
    return await checked_request(
        client, "POST", "/api/buyers", expected_status=201, json=buyer_data
    )


async def get_or_create_location(
    client: httpx.AsyncClient, location_data: dict[str, Any], buyer_id: int
) -> dict[str, Any]:
    locations = await checked_request(
        client, "GET", "/api/locations", expected_status=200, params={"limit": 500}
    )
    payload = {
        "name": location_data["name"],
        "buyer_id": buyer_id,
        "latitude": location_data["latitude"],
        "longitude": location_data["longitude"],
    }
    for location in locations:
        if location["name"] == payload["name"] and location["buyer_id"] == buyer_id:
            return await checked_request(
                client,
                "PUT",
                f"/api/locations/{location['id']}",
                expected_status=200,
                json=payload,
            )
    return await checked_request(
        client, "POST", "/api/locations", expected_status=201, json=payload
    )


async def upsert_price(
    client: httpx.AsyncClient,
    location_id: str,
    commodity: str,
    price_per_tonne: str,
    effective_date: str,
) -> dict[str, Any]:
    prices = await checked_request(
        client,
        "GET",
        "/api/prices",
        expected_status=200,
        params={"location_id": location_id, "commodity": commodity, "limit": 500},
    )
    payload = {
        "location_id": location_id,
        "commodity": commodity,
        "price_per_tonne": price_per_tonne,
        "effective_date": effective_date,
    }
    if prices:
        return await checked_request(
            client,
            "PUT",
            f"/api/prices/{prices[0]['id']}",
            expected_status=200,
            json=payload,
        )
    return await checked_request(client, "POST", "/api/prices", expected_status=201, json=payload)


async def verify_nearby(
    client: httpx.AsyncClient,
    location: dict[str, Any],
    commodity: str,
    radius_km: float,
) -> None:
    results = await checked_request(
        client,
        "GET",
        "/api/locations/nearby",
        expected_status=200,
        params={
            "lat": location["latitude"],
            "lon": location["longitude"],
            "radius_km": radius_km,
            "commodity": commodity,
            "limit": 50,
        },
    )
    match = next((item for item in results if item["id"] == location["id"]), None)
    if match is None:
        raise RuntimeError(
            f"Nearby lookup did not return seeded location {location['name']!r} "
            f"for commodity {commodity!r}"
        )
    if match["buyer"]["id"] != location["buyer_id"]:
        raise RuntimeError(f"Nearby lookup returned the wrong buyer for {location['name']!r}")
    if not any(price["commodity"] == commodity for price in match["prices"]):
        raise RuntimeError(f"Nearby lookup did not include the {commodity!r} price")


async def seed(base_url: str, radius_km: float, timeout: float) -> None:
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        buyers = {
            buyer_data["name"]: await get_or_create_buyer(client, buyer_data)
            for buyer_data in BUYERS
        }
        effective_date = datetime.now(UTC).replace(microsecond=0).isoformat()

        for location_data in LOCATIONS:
            buyer = buyers[location_data["buyer_name"]]
            location = await get_or_create_location(client, location_data, buyer["id"])
            for commodity, price_per_tonne in location_data["prices"].items():
                await upsert_price(
                    client,
                    location["id"],
                    commodity,
                    price_per_tonne,
                    effective_date,
                )
                await verify_nearby(client, location, commodity, radius_km)
                print(
                    f"Verified {commodity} at {location['name']}: "
                    f"AUD {price_per_tonne}/tonne within {radius_km:g} km"
                )


def main() -> None:
    args = parse_args()
    asyncio.run(seed(args.base_url, args.radius_km, args.timeout))


if __name__ == "__main__":
    main()
