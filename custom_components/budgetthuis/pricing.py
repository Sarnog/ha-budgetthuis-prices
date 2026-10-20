"""Customer-contract price calculation.

Applies the same breakdown shown on the Budget Thuis app's own tariff screen -
beursprijs + energiebelasting with BTW, plus the inkoopvergoeding - to the live
per-hour beursprijs (spot price) and energiebelasting parsed from the tariff
page, using the customer's own inkoopvergoeding instead of trusting the
site's own displayed all-in price. energiebelasting is a government-set tax
rate, not a Budget Thuis one, and the tariff page already publishes its net
amount per hour (EnergyTax.AmountNet) - so unlike inkoopvergoeding, there's
nothing customer-specific to configure for it. Kept free of Home Assistant
imports so it's unit testable with plain pytest, same as parser.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser import HourPrice


@dataclass
class ContractConfig:
    """The customer-specific components of the tariff breakdown.

    inkoopvergoeding is the amount *including* BTW, exactly as the Budget
    Thuis app shows it, so it's added after BTW instead of taxed again.
    """

    inkoopvergoeding: float
    vat_percent: float
    beursprijs_markup: float = 0.0


def calculate_price(hour: HourPrice, config: ContractConfig) -> float | None:
    """Compute the customer-accurate all-in price for one hour.

    Returns None if the page didn't carry a beursprijs (Commodity.AmountNet)
    or energiebelasting (EnergyTax.AmountNet) for this hour - there's nothing
    to base the calculation on.
    """
    if hour.commodity_net is None or hour.energy_tax_net is None:
        return None

    subtotal = hour.commodity_net + config.beursprijs_markup + hour.energy_tax_net
    return round(subtotal * (1 + config.vat_percent / 100) + config.inkoopvergoeding, 3)
