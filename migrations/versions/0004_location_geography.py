"""Use indexed geography for meter-based location proximity queries.

Revision ID: 0004_location_geography
Revises: 0003_price_uuid_location
"""

from alembic import op

revision = "0004_location_geography"
down_revision = "0003_price_uuid_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX idx_locations_point_gist")
    op.execute(
        """
        ALTER TABLE locations
        ALTER COLUMN point TYPE geography(POINT, 4326)
        USING point::geography
        """
    )
    op.execute("CREATE INDEX idx_locations_point_gist ON locations USING GIST(point)")


def downgrade() -> None:
    op.execute("DROP INDEX idx_locations_point_gist")
    op.execute(
        """
        ALTER TABLE locations
        ALTER COLUMN point TYPE geometry(POINT, 4326)
        USING point::geometry
        """
    )
    op.execute("CREATE INDEX idx_locations_point_gist ON locations USING GIST(point)")
