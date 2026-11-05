"""Associate locations with buyers.

Revision ID: 0005_location_buyer
Revises: 0004_location_geography
"""

from alembic import op

revision = "0005_location_buyer"
down_revision = "0004_location_geography"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE locations ADD COLUMN buyer_id INTEGER")
    op.execute(
        """
        WITH legacy_buyer AS (
            INSERT INTO buyers (name)
            SELECT 'Legacy location owner'
            WHERE EXISTS (SELECT 1 FROM locations)
            RETURNING id
        )
        UPDATE locations
        SET buyer_id = (SELECT id FROM legacy_buyer)
        WHERE buyer_id IS NULL
        """
    )
    op.execute("ALTER TABLE locations ALTER COLUMN buyer_id SET NOT NULL")
    op.execute(
        """
        ALTER TABLE locations
        ADD CONSTRAINT fk_locations_buyer_id_buyers
        FOREIGN KEY (buyer_id) REFERENCES buyers(id) ON DELETE RESTRICT
        """
    )
    op.execute("CREATE INDEX ix_locations_buyer_id ON locations (buyer_id)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_locations_buyer_id")
    op.execute("ALTER TABLE locations DROP CONSTRAINT fk_locations_buyer_id_buyers")
    op.execute("ALTER TABLE locations DROP COLUMN buyer_id")
