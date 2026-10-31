from decimal import Decimal

from harvest_edge.services.pricing import calculate_netback


def test_netback_subtracts_costs_and_uncertainty() -> None:
    costs, netback = calculate_netback(
        Decimal("410.00"),
        Decimal("38.50"),
        Decimal("8.00"),
        Decimal("12.50"),
        Decimal("5.00"),
    )

    assert costs == Decimal("59.00")
    assert netback == Decimal("346.00")


def test_netback_can_be_negative() -> None:
    _, netback = calculate_netback(
        Decimal("50.00"),
        Decimal("38.50"),
        Decimal("8.00"),
        Decimal("12.50"),
        Decimal("5.00"),
    )

    assert netback == Decimal("-14.00")
