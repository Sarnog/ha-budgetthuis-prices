"""Terugleverprijs per uur: saldering tot 2027, daarna beursprijs plus ZonneBonus.

Budget Thuis geeft de ZonneBonus in vaste maandelijkse tijdvakken "tussen
zonsopkomst en zonsondergang" (bijvoorbeeld juni 05:00-22:00 en september
07:00-20:00), maar publiceert de volledige tabel niet. Het tijdvak wordt daarom
benaderd: de vroegste zonsopkomst en de laatste zonsondergang van die maand op
de locatie van Home Assistant, elk afgerond op het dichtstbijzijnde hele uur.
Voor De Bilt geeft dat precies de twee voorbeelden van Budget Thuis.

Bevat geen Home Assistant-imports, zodat het met gewone pytest te testen is,
net als pricing.py.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache

from astral import Observer
from astral.sun import sun

from .const import PRICE_DECIMALS, SALDERING_END_YEAR
from .parser import AMSTERDAM, HourPrice


@dataclass(frozen=True)
class Location:
    """De plek waarvoor zonsopkomst en zonsondergang bepaald worden."""

    latitude: float
    longitude: float


@dataclass(frozen=True)
class ExportConfig:
    """De instellingen van de ZonneBonus, voor de locatie van Home Assistant.

    bonus_percent 0 zet de bonus uit; de terugleverprijs is dan de beursprijs.
    De bonus geldt van bonus_from tot en met bonus_until (None = geen einde).
    """

    location: Location
    bonus_percent: float
    bonus_max_beursprijs: float
    bonus_from: date
    bonus_until: date | None = None

    def in_bonus_period(self, day: date) -> bool:
        """Valt deze dag binnen de ingestelde periode van de ZonneBonus?"""
        return self.bonus_from <= day and (
            self.bonus_until is None or day <= self.bonus_until
        )


def _round_to_hour(moment: datetime) -> time:
    """Rond een klokkijd af op het dichtstbijzijnde hele uur."""
    rounded = (moment + timedelta(minutes=30)).replace(
        minute=0, second=0, microsecond=0
    )
    return rounded.time()


@lru_cache(maxsize=24)
def bonus_window(location: Location, year: int, month: int) -> tuple[time, time]:
    """Het tijdvak van de ZonneBonus in een maand, in Amsterdamse kloktijd."""
    observer = Observer(latitude=location.latitude, longitude=location.longitude)
    days = [
        date(year, month, day)
        for day in range(1, calendar.monthrange(year, month)[1] + 1)
    ]
    events = [sun(observer, date=day, tzinfo=AMSTERDAM) for day in days]
    sunrise = min(events, key=lambda e: e["sunrise"].time())["sunrise"]
    sunset = max(events, key=lambda e: e["sunset"].time())["sunset"]
    return _round_to_hour(sunrise), _round_to_hour(sunset)


def _in_bonus_window(hour: HourPrice, location: Location) -> bool:
    """Valt het hele uur binnen het tijdvak van de ZonneBonus?"""
    start = hour.start.astimezone(AMSTERDAM)
    end = hour.end.astimezone(AMSTERDAM)
    window_start, window_end = bonus_window(location, start.year, start.month)
    # Een uur dat om middernacht eindigt, telt als einde 24:00 van die dag.
    end_time = time.max if end.date() > start.date() else end.time()
    return window_start <= start.time() and end_time <= window_end


def calculate_export_price(
    hour: HourPrice, contract_price: float | None, config: ExportConfig
) -> float | None:
    """De opbrengst van één teruggeleverde kWh in dit uur.

    Met saldering (voor 2027) is dat de contractprijs van het uur. Daarna de
    beursprijs, plus de ZonneBonus binnen de ingestelde periode, binnen het
    tijdvak en bij een positieve beursprijs. Geeft None als de benodigde prijs
    ontbreekt.
    """
    start = hour.start.astimezone(AMSTERDAM)
    if start.year < SALDERING_END_YEAR:
        return contract_price

    beursprijs = hour.commodity_net
    if beursprijs is None:
        return None

    bonus = 0.0
    if (
        beursprijs > 0
        and config.in_bonus_period(start.date())
        and _in_bonus_window(hour, config.location)
    ):
        bonus = (
            config.bonus_percent / 100 * min(beursprijs, config.bonus_max_beursprijs)
        )
    return round(beursprijs + bonus, PRICE_DECIMALS)
