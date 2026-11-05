# Harvest Edge

Australian grain bid, receival schedule, and export netback API. The service uses
FastAPI, SQLAlchemy 2 async sessions, PostgreSQL/PostGIS, Alembic, and Pydantic v2.

## Local setup

Requires Python 3.11+ and Docker Compose.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
docker compose up --build -d
docker compose exec web alembic upgrade head
docker compose run --rm test
```

The API is available at `http://localhost:8000`; OpenAPI docs are at `/docs`.
`GET /health` is a liveness check and `GET /ready` checks database connectivity.
Compose waits for PostGIS readiness before starting the API and test runner.
The test runner creates and uses a separate `harvest_edge_test` database.
The example `postgres` credentials are for local development only; set unique
strong credentials and URL-encode special characters in database URLs for
deployments.

## API

- `GET`, `POST`, `PUT`, and `DELETE /api/buyers` manage buyer records.
- `GET`, `POST`, `PUT`, and `DELETE /api/locations` manage named locations;
	creation and updates accept latitude/longitude coordinates and store an SRID
	4326 PostGIS geography point. Location IDs are UUIDs. `GET /api/locations/nearby`
	accepts `lat`, `lon`, optional `radius_km` (default 50), and an optional
	`commodity` filter, plus `limit` (default 50, maximum 200) and `offset`
	pagination; it returns matching locations, their buyers, and advertised prices.
	Locations are assigned to a buyer by `buyer_id`.
- `GET`, `POST`, `PUT`, and `DELETE /api/prices` manage grain prices. Listing
	supports optional `location_id` and `commodity` filters.
- `GET /api/bids` accepts `receival_site_id`, `commodity_id`, `grade_id`,
	`season_id`, and `delivery_window_id` filters.
- `GET /api/netback` requires `receival_site_id`, `port_terminal_id`, and
	`commodity_id`. Grade, season, delivery window, and `as_of_date` are optional.
- Bid and netback responses include a top-level `provenance.sources` collection.
	Each source has publisher, URL, retrieved/published timestamps, verification
	status, and licence restrictions.

Netback is calculated as FOB export price less freight, receival, and handling
costs, then less the sum of the bid and charge uncertainty margins. Values are
AUD per tonne; negative netbacks are returned as-is.

### Authentication

`POST /api/buyers`, `POST /api/locations`, and `POST /api/prices` require an
`X-API-Key` or an `Authorization: Bearer <JWT>` credential with the
`write:prices` scope. `POST /api/admin/keys` requires `admin:all`. API keys are
shown only when created; only their SHA-256 hashes are stored. Keep the one-time
response secure. Bootstrap the first global administrator key through a trusted
offline provisioning process.

Bearer tokens use HS256 and require an `exp` claim. Configure
`HARVEST_EDGE_JWT_SECRET_KEY` with a secret of at least 32 characters. When
configured, `HARVEST_EDGE_JWT_ISSUER` and `HARVEST_EDGE_JWT_AUDIENCE` are also
validated. Token scopes may be provided as a space-delimited `scope` string or
a `scopes` string array; an optional integer `buyer_id` is returned in the
principal context. Without the JWT secret, bearer tokens are rejected.

## Ingestion

`PublicCashBidScraper` and `ReceivalScheduleScraper` parse configurable public
HTML tables. Configure `column_map` to map normalized fields to exact upstream
column labels, then pass the scraper and a persistence processor to
`IngestionRunner.run`. The runner rate-limits and retries upstream requests,
persists a running log before work starts, and records completion counts or a
bounded error payload. Source URLs and field mappings are intentionally supplied
by deployment configuration rather than fabricated for publishers.

## Operations

Set `HARVEST_EDGE_DATABASE_URL` and the `HARVEST_EDGE_*` settings in the runtime
environment. Apply migrations as a release step using `alembic upgrade head`;
the database role must be allowed to install/use PostGIS for the initial
migration. The included Compose credentials are for local development only.

Run checks with `pytest` and `ruff check src tests migrations`.

## Mock data seeding

With the API and PostGIS database running and migrations applied, install the
project dependencies and run the idempotent demo seeder:

```bash
pip install -e .
python scripts/seed_data.py
```

The script creates or reuses two buyers, their locations, and Wheat, Barley,
and Canola prices. Price records are AUD per tonne in this API; currency is
implicit and is not a separate request field. It checks every seeded record
through `GET /api/locations/nearby` with a commodity filter and fails if the
location, associated buyer, or matching price is absent. Point it at another
running API with `HARVEST_EDGE_API_URL=http://host:8000` or `--base-url`.
`--radius-km` defaults to 10 and accepts values up to the API's 500 km ceiling.

## Partner price ingestion plan

For recurring partner updates, prefer a separate ingestion worker over
in-process FastAPI background tasks:

1. Implement a partner adapter that fetches a feed and maps it into validated
   canonical records (`location_id`, `commodity`, `price_per_tonne`, and
   timezone-aware `effective_date`), preserving source identifiers and
   retrieval metadata.
2. Add an authenticated `POST /api/prices/bulk-upload` endpoint with a bounded
   batch size, strict per-record Pydantic validation, and an explicit
   all-or-nothing transaction policy. Add a unique idempotency key (for example
   source, location, commodity, and effective date) and use PostgreSQL upserts
   so retries do not duplicate prices.
3. Run recurring fetches in a separate Arq worker with a Redis queue, persisted
   retry/backoff state, and a single-flight lock per partner. Keep request
   handling independent from feed latency and transient partner outages.
4. Record each run and rejected-record summaries in ingestion logs; emit
   structured metrics for records accepted/rejected, retries, and feed
   freshness. Protect partner credentials in deployment secrets.
5. Test adapter parsing, duplicate/retry behavior, transaction rollback,
   authorization, batch-size limits, and database-to-nearby API visibility
   against PostGIS before enabling schedules in production.