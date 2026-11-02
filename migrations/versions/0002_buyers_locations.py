"""Add buyers and spatial locations.

Revision ID: 0002_buyers_locations
Revises: 0001_initial_schema
"""

from alembic import op

revision = "0002_buyers_locations"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE buyers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(254),
            phone VARCHAR(30),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE locations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL
                CONSTRAINT ck_locations_latitude_range CHECK (latitude BETWEEN -90 AND 90),
            longitude DOUBLE PRECISION NOT NULL
                CONSTRAINT ck_locations_longitude_range CHECK (longitude BETWEEN -180 AND 180),
            point geometry(POINT, 4326) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_locations_point_gist ON locations USING GIST(point)")


def downgrade() -> None:
    op.execute("DROP TABLE locations")
    op.execute("DROP TABLE buyers")
