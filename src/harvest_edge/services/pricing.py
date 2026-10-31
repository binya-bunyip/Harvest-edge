from decimal import Decimal


def calculate_netback(
    fob_price: Decimal,
    freight_cost: Decimal,
    receival_fee: Decimal,
    handling_fee: Decimal,
    uncertainty_margin: Decimal,
) -> tuple[Decimal, Decimal]:
    total_costs = freight_cost + receival_fee + handling_fee
    return total_costs, fob_price - total_costs - uncertainty_margin
