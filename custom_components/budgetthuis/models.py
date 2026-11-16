"""Datamodellen met de geprijsde tarieven, gedeeld door de hele integratie.

Bevat geen Home Assistant-imports, zodat stats.py ze kan gebruiken en het met
gewone pytest te testen blijft, net als parser.py en pricing.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .parser import AMSTERDAM


@dataclass
class PricedHour:
    """De prijs van één blok: de prijs voor het eigen contract (price), de
    all-in prijs die Budget Thuis zelf toont (site_price) en, alleen bij stroom,
    de opbrengst van een teruggeleverde kWh (export_price)."""

    start: datetime
    end: datetime
    price: float | None
    site_price: float | None
    export_price: float | None = None


def _local_today() -> date:
    """De datum van vandaag op de (Amsterdamse) kalender van de tarievenpagina."""
    return datetime.now(AMSTERDAM).date()


@dataclass
class BudgetThuisData:
    """Geprijsde tariefgegevens voor elke dag op de pagina, per ISO-datum.

    "Vandaag" en "morgen" worden bij het uitlezen aan de klok gekoppeld in
    plaats van bij het ophalen, zodat "morgen" van gisteren om middernacht
    meteen "vandaag" wordt en niet pas bij de volgende ophaalronde.
    """

    electricity: dict[str, list[PricedHour]]
    gas: dict[str, list[PricedHour]]

    @staticmethod
    def _day(by_date: dict[str, list[PricedHour]], offset: int) -> list[PricedHour]:
        return by_date.get((_local_today() + timedelta(days=offset)).isoformat(), [])

    @property
    def today(self) -> list[PricedHour]:
        return self._day(self.electricity, 0)

    @property
    def tomorrow(self) -> list[PricedHour]:
        return self._day(self.electricity, 1)

    @property
    def tomorrow_valid(self) -> bool:
        return len(self.tomorrow) > 0

    @property
    def gas_today(self) -> list[PricedHour]:
        return self._day(self.gas, 0)

    @property
    def gas_tomorrow(self) -> list[PricedHour]:
        return self._day(self.gas, 1)

    @property
    def gas_tomorrow_valid(self) -> bool:
        return len(self.gas_tomorrow) > 0
