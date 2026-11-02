from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from harvest_edge.schemas.price import PriceCreate


def test_price_create_normalizes_commodity_and_effective_date_to_utc() -> None:
    non_utc = timezone(timedelta(hours=10))
    payload = PriceCreate(
        location_id=uuid4(),
        commodity="  Wheat ",
        price_per_tonne=Decimal("321.45"),
        effective_date=datetime(2026, 11, 2, 14, tzinfo=non_utc),
    )

    assert payload.commodity == "Wheat"
    assert payload.effective_date == datetime(2026, 11, 2, 4, tzinfo=UTC)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("commodity", "  "),
        ("price_per_tonne", Decimal("0")),
        ("price_per_tonne", Decimal("-1")),
        ("effective_date", datetime(2026, 11, 2)),
    ],
)
def test_price_create_rejects_invalid_values(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "location_id": uuid4(),
        "commodity": "Wheat",
        "price_per_tonne": Decimal("321.45"),
        "effective_date": datetime(2026, 11, 2, tzinfo=UTC),
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        PriceCreate.model_validate(payload)
