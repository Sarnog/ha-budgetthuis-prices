"""Statistieken over de uurprijzen (PricedHour) van één dag.

Werkt structureel op alles met de vorm van coordinator.PricedHour (start, end,
price). PricedHour wordt alleen voor typering geïmporteerd, dus deze module
heeft geen Home Assistant nodig en is met gewone pytest te testen, net als
parser.py en pricing.py.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from .const import PRICE_DECIMALS

if TYPE_CHECKING:
    from .coordinator import PricedHour


def hour_for(hours: list[PricedHour], moment: datetime) -> PricedHour | None:
    """Het blok waarin moment valt, vergeleken als absolute tijdstippen.

    Datetimes met dezelfde tzinfo vergelijken op de klok en negeren de
    zomertijd-fold. De twee uren 02:00-03:00 bij de overgang in de herfst zijn
    met gewone < vergelijkingen dus niet te onderscheiden.
    """
    instant = moment.timestamp()
    for hour in hours:
        if hour.start.timestamp() <= instant < hour.end.timestamp():
            return hour
    return None


def priced(hours: list[PricedHour]) -> list[float]:
    """Alleen de uren waarvan de prijs voor het eigen contract te berekenen was."""
    return [h.price for h in hours if h.price is not None]


def average(hours: list[PricedHour]) -> float | None:
    prices = priced(hours)
    if not prices:
        return None
    return round(sum(prices) / len(prices), PRICE_DECIMALS)


def lowest(hours: list[PricedHour]) -> float | None:
    return min(priced(hours), default=None)


def highest(hours: list[PricedHour]) -> float | None:
    return max(priced(hours), default=None)


def _runs(
    hours: list[PricedHour], predicate: Callable[[float], bool]
) -> list[list[PricedHour]]:
    """Groepeer uren in zo lang mogelijke reeksen waarvoor predicate(price) geldt."""
    runs: list[list[PricedHour]] = []
    current: list[PricedHour] = []
    for hour in hours:
        if hour.price is not None and predicate(hour.price):
            current.append(hour)
        else:
            if current:
                runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _run_average(run: list[PricedHour]) -> float:
    """Het gemiddelde van een reeks; alle uren in een reeks hebben een prijs."""
    prices = priced(run)
    return sum(prices) / len(prices)


def _period(run: list[PricedHour]) -> tuple[datetime, datetime, float]:
    return run[0].start, run[-1].end, round(_run_average(run), PRICE_DECIMALS)


def cheapest_period(hours: list[PricedHour]) -> tuple[datetime, datetime, float] | None:
    """De aaneengesloten reeks onder het daggemiddelde met de laagste gemiddelde prijs.

    De lengte volgt de prijsvorm van die dag, van één uur tot bijna de hele dag,
    en is dus geen vast ingesteld venster. Geeft (start, einde, gemiddelde prijs),
    of None als er geen prijzen zijn.
    """
    day_average = average(hours)
    if day_average is None:
        return None

    # Het daggemiddelde ligt nooit onder de laagste prijs, dus er is altijd
    # minstens één uur dat meetelt: een lege reeks kan hier niet voorkomen.
    runs = _runs(hours, lambda price: price <= day_average)
    cheapest_run = min(runs, key=_run_average)
    return _period(cheapest_run)


def most_expensive_period(
    hours: list[PricedHour],
) -> tuple[datetime, datetime, float] | None:
    """De aaneengesloten reeks boven het daggemiddelde met de hoogste gemiddelde prijs.

    Spiegel van cheapest_period(). Geeft None als er geen prijzen zijn, of als
    elk uur op of onder het daggemiddelde ligt (bijvoorbeeld bij overal dezelfde
    prijs): dan bestaat er geen reeks boven het gemiddelde.
    """
    day_average = average(hours)
    if day_average is None:
        return None

    runs = _runs(hours, lambda price: price > day_average)
    if not runs:
        return None

    priciest_run = max(runs, key=_run_average)
    return _period(priciest_run)
