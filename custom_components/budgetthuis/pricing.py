"""Customer-contract price calculation.

Applies the same breakdown shown on the Budget Thuis app's own tariff screen -
beursprijs + inkoopvergoeding + energiebelasting, then BTW - to the live
per-hour beursprijs (spot price) parsed from the tariff page, using the
customer's own contract values instead of trusting the site's own displayed
all-in price. Kept free of Home Assistant imports so it's unit testable with
plain pytest, same as parser.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from .parser import HourPrice


@dataclass
class ContractConfig:
    """The customer-specific components of the tariff breakdown."""

    inkoopvergoeding: float
    energiebelasting: float
    vat_percent: float
    beursprijs_markup: float = 0.0


def calculate_price(hour: HourPrice, config: ContractConfig) -> float | None:
    """Compute the customer-accurate all-in price for one hour.

    Returns None if the page didn't carry a beursprijs (Commodity.AmountNet)
    for this hour - there's nothing to base the calculation on.
    """
    if hour.commodity_net is None:
        return None

    subtotal = (
        hour.commodity_net
        + config.beursprijs_markup
        + config.inkoopvergoeding
        + config.energiebelasting
    )
    return round(subtotal * (1 + config.vat_percent / 100), 5)
