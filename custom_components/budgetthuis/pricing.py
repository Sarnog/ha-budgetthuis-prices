"""Prijsberekening voor het eigen contract.

Past dezelfde opbouw toe als het tarievenscherm in de Budget Thuis-app:
beursprijs + energiebelasting met BTW, plus de inkoopvergoeding. De beursprijs
en de energiebelasting komen live per uur van de tarievenpagina; de
inkoopvergoeding is die van het eigen contract en niet de all-in prijs die de
site zelf toont. De energiebelasting is een door de overheid vastgesteld tarief
(voor elke leverancier gelijk) en staat per uur op de pagina
(EnergyTax.AmountNet), dus daar valt niets in te stellen.

Bevat geen Home Assistant-imports, zodat het met gewone pytest te testen is,
net als parser.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import PRICE_DECIMALS
from .parser import HourPrice


@dataclass
class ContractConfig:
    """De contractgebonden onderdelen van de tariefopbouw.

    inkoopvergoeding is het bedrag *inclusief* BTW, precies zoals de Budget
    Thuis-app het toont. Het wordt daarom na de BTW opgeteld en niet nogmaals
    belast.
    """

    inkoopvergoeding: float
    vat_percent: float
    beursprijs_markup: float = 0.0


def calculate_price(hour: HourPrice, config: ContractConfig) -> float | None:
    """Bereken de all-in prijs voor één uur, voor het eigen contract.

    Geeft None als de pagina voor dit uur geen beursprijs (Commodity.AmountNet)
    of energiebelasting (EnergyTax.AmountNet) bevat: dan is er niets om op te
    rekenen.
    """
    if hour.commodity_net is None or hour.energy_tax_net is None:
        return None

    subtotal = hour.commodity_net + config.beursprijs_markup + hour.energy_tax_net
    return round(
        subtotal * (1 + config.vat_percent / 100) + config.inkoopvergoeding,
        PRICE_DECIMALS,
    )
