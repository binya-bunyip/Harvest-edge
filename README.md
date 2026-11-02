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
docker compose up -d db
alembic upgrade head
uvicorn harvest_edge.main:app --reload --app-dir src
```

The API is available at `http://localhost:8000`; OpenAPI docs are at `/docs`.
`GET /health` is a liveness check and `GET /ready` checks database connectivity.

## API

- `GET`, `POST`, `PUT`, and `DELETE /api/buyers` manage buyer records.
- `GET`, `POST`, `PUT`, and `DELETE /api/locations` manage named locations;
	creation and updates accept latitude/longitude coordinates and store an SRID
	4326 PostGIS point. Location IDs are UUIDs.
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