"""Create the initial Harvest Edge schema.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in """
        CREATE EXTENSION IF NOT EXISTS postgis;
        CREATE TABLE operators (
            id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE,
            abn VARCHAR(11) UNIQUE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE receival_sites (
            id SERIAL PRIMARY KEY, operator_id INTEGER NOT NULL REFERENCES operators(id) ON DELETE RESTRICT,
            name VARCHAR(200) NOT NULL, code VARCHAR(40) NOT NULL UNIQUE, state VARCHAR(3) NOT NULL,
            postcode VARCHAR(4), location geometry(POINT, 4326) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_receival_sites_operator_id ON receival_sites(operator_id);
        CREATE INDEX idx_receival_sites_location_gist ON receival_sites USING GIST(location);
        CREATE TABLE port_terminals (
            id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE, state VARCHAR(3) NOT NULL,
            location geometry(POINT, 4326) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_port_terminals_location_gist ON port_terminals USING GIST(location);
        CREATE TABLE freight_corridors (
            id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
            origin_site_id INTEGER NOT NULL REFERENCES receival_sites(id) ON DELETE RESTRICT,
            destination_terminal_id INTEGER NOT NULL REFERENCES port_terminals(id) ON DELETE RESTRICT,
            route geometry(LINESTRING, 4326) NOT NULL, distance_km NUMERIC(10, 2) NOT NULL CHECK (distance_km > 0),
            effective_start_date DATE NOT NULL, effective_end_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_freight_corridors_valid_dates CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date)
        );
        CREATE INDEX ix_freight_corridors_origin_site_id ON freight_corridors(origin_site_id);
        CREATE INDEX ix_freight_corridors_destination_terminal_id ON freight_corridors(destination_terminal_id);
        CREATE INDEX idx_freight_corridors_route_gist ON freight_corridors USING GIST(route);
        CREATE TABLE commodities (
            id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, code VARCHAR(30) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE grades (
            id SERIAL PRIMARY KEY, commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE RESTRICT,
            name VARCHAR(100) NOT NULL, code VARCHAR(30) NOT NULL,
            effective_start_date DATE NOT NULL, effective_end_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_grades_commodity_code UNIQUE (commodity_id, code),
            CONSTRAINT ck_grades_valid_dates CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date)
        );
        CREATE INDEX ix_grades_commodity_id ON grades(commodity_id);
        CREATE TABLE seasons (
            id SERIAL PRIMARY KEY, name VARCHAR(80) NOT NULL UNIQUE, start_date DATE NOT NULL, end_date DATE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_seasons_valid_season_dates CHECK (end_date >= start_date)
        );
        CREATE TABLE delivery_windows (
            id SERIAL PRIMARY KEY,
            receival_site_id INTEGER NOT NULL REFERENCES receival_sites(id) ON DELETE RESTRICT,
            season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE RESTRICT,
            name VARCHAR(100) NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL,
            effective_start_date DATE NOT NULL, effective_end_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_delivery_windows_valid_window_dates CHECK (end_date >= start_date),
            CONSTRAINT ck_delivery_windows_valid_dates CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date),
            CONSTRAINT uq_delivery_windows_site_season_name UNIQUE (receival_site_id, season_id, name)
        );
        CREATE INDEX ix_delivery_windows_receival_site_id ON delivery_windows(receival_site_id);
        CREATE INDEX ix_delivery_windows_season_id ON delivery_windows(season_id);
        CREATE TABLE data_sources (
            id SERIAL PRIMARY KEY, name VARCHAR(160) NOT NULL UNIQUE, publisher_name VARCHAR(200) NOT NULL,
            source_url VARCHAR(2048) NOT NULL, verification_status VARCHAR(40) NOT NULL DEFAULT 'unverified',
            licence_restrictions VARCHAR(1000), retrieved_at TIMESTAMPTZ NOT NULL, published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE buyer_bids (
            id SERIAL PRIMARY KEY,
            receival_site_id INTEGER NOT NULL REFERENCES receival_sites(id) ON DELETE RESTRICT,
            commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE RESTRICT,
            grade_id INTEGER NOT NULL REFERENCES grades(id) ON DELETE RESTRICT,
            season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE RESTRICT,
            delivery_window_id INTEGER NOT NULL REFERENCES delivery_windows(id) ON DELETE RESTRICT,
            data_source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,
            bid_price_aud_per_tonne NUMERIC(12, 2) NOT NULL CHECK (bid_price_aud_per_tonne >= 0),
            fob_export_price_aud_per_tonne NUMERIC(12, 2) CHECK (fob_export_price_aud_per_tonne IS NULL OR fob_export_price_aud_per_tonne >= 0),
            uncertainty_margin_aud_per_tonne NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (uncertainty_margin_aud_per_tonne >= 0),
            quoted_at TIMESTAMPTZ NOT NULL, effective_start_date DATE NOT NULL, effective_end_date DATE,
            raw_payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_buyer_bids_valid_dates CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date)
        );
        CREATE INDEX ix_buyer_bids_receival_site_id ON buyer_bids(receival_site_id);
        CREATE INDEX ix_buyer_bids_commodity_id ON buyer_bids(commodity_id);
        CREATE INDEX ix_buyer_bids_grade_id ON buyer_bids(grade_id);
        CREATE INDEX ix_buyer_bids_season_id ON buyer_bids(season_id);
        CREATE INDEX ix_buyer_bids_delivery_window_id ON buyer_bids(delivery_window_id);
        CREATE INDEX ix_buyer_bids_data_source_id ON buyer_bids(data_source_id);
        CREATE TABLE handling_freight_charges (
            id SERIAL PRIMARY KEY,
            receival_site_id INTEGER NOT NULL REFERENCES receival_sites(id) ON DELETE RESTRICT,
            port_terminal_id INTEGER NOT NULL REFERENCES port_terminals(id) ON DELETE RESTRICT,
            commodity_id INTEGER REFERENCES commodities(id) ON DELETE RESTRICT,
            data_source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,
            freight_cost_aud_per_tonne NUMERIC(12, 2) NOT NULL CHECK (freight_cost_aud_per_tonne >= 0),
            receival_fee_aud_per_tonne NUMERIC(12, 2) NOT NULL CHECK (receival_fee_aud_per_tonne >= 0),
            handling_fee_aud_per_tonne NUMERIC(12, 2) NOT NULL CHECK (handling_fee_aud_per_tonne >= 0),
            uncertainty_margin_aud_per_tonne NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (uncertainty_margin_aud_per_tonne >= 0),
            effective_start_date DATE NOT NULL, effective_end_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_handling_freight_charges_valid_dates CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date)
        );
        CREATE INDEX ix_handling_freight_charges_receival_site_id ON handling_freight_charges(receival_site_id);
        CREATE INDEX ix_handling_freight_charges_port_terminal_id ON handling_freight_charges(port_terminal_id);
        CREATE INDEX ix_handling_freight_charges_commodity_id ON handling_freight_charges(commodity_id);
        CREATE INDEX ix_handling_freight_charges_data_source_id ON handling_freight_charges(data_source_id);
        CREATE TABLE ingestion_logs (
            id SERIAL PRIMARY KEY, data_source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,
            scraper_name VARCHAR(160) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'running'
                CHECK (status IN ('running', 'succeeded', 'failed')),
            started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ,
            records_processed INTEGER NOT NULL DEFAULT 0 CHECK (records_processed >= 0), error_payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_ingestion_logs_data_source_id ON ingestion_logs(data_source_id);
    """.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for statement in """
        DROP TABLE ingestion_logs;
        DROP TABLE handling_freight_charges;
        DROP TABLE buyer_bids;
        DROP TABLE data_sources;
        DROP TABLE delivery_windows;
        DROP TABLE seasons;
        DROP TABLE grades;
        DROP TABLE commodities;
        DROP TABLE freight_corridors;
        DROP TABLE port_terminals;
        DROP TABLE receival_sites;
        DROP TABLE operators;
    """.split(";"):
        if statement.strip():
            op.execute(statement)
