from unittest.mock import AsyncMock, MagicMock

import pytest
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from harvest_edge.models import Buyer, Location
from harvest_edge.services.geospatial import get_locations_nearby


@pytest.mark.asyncio
async def test_nearby_query_uses_indexable_geography_distance_and_commodity_filter() -> None:
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.tuples.return_value.all.return_value = []
    db.execute.return_value = result

    locations = await get_locations_nearby(
        db, -33.86, 151.2, 12.5, "Wheat", limit=20, offset=10
    )

    statement = db.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert locations == []
    assert "ST_DWithin" in sql
    assert "prices.commodity" in sql
    assert "buyers.id = locations.buyer_id" in sql
    assert "LIMIT" in sql
    assert "OFFSET" in sql
    assert "Wheat" in compiled.params.values()
    assert 12_500.0 in compiled.params.values()
    assert isinstance(Location.__table__.c.point.type, Geography)
    assert any(index.name == "idx_locations_point_gist" for index in Location.__table__.indexes)
    buyer_foreign_key = next(iter(Location.__table__.c.buyer_id.foreign_keys))
    assert buyer_foreign_key.target_fullname == "buyers.id"
    assert Buyer.locations.property.cascade.delete_orphan
    assert Location.prices.property.cascade.delete_orphan
