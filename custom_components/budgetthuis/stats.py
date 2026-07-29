"""Pure hourly-price statistics over a day's PricedHours.

Operates structurally on anything shaped like coordinator.PricedHour (start,
end, price) - PricedHour itself is only imported for type checking, so this
module carries no Home Assistant dependency and is unit testable with plain
pytest, same as parser.py/pricing.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .coordinator import PricedHour


def hour_for(hours: list[PricedHour], moment: datetime) -> PricedHour | None:
    for hour in hours:
        if hour.start <= moment < hour.end:
            return hour
    return None


def priced(hours: list[PricedHour]) -> list[float]:
    """Only the hours whose customer price could actually be calculated."""
    return [h.price for h in hours if h.price is not None]


def average(hours: list[PricedHour]) -> float | None:
    prices = priced(hours)
    if not prices:
        return None
    return round(sum(prices) / len(prices), 3)


def lowest(hours: list[PricedHour]) -> float | None:
    return min(priced(hours), default=None)


def highest(hours: list[PricedHour]) -> float | None:
    return max(priced(hours), default=None)


def _runs(hours: list[PricedHour], predicate: Callable[[float], bool]) -> list[list[PricedHour]]:
    """Group hours into maximal consecutive runs matching predicate(price)."""
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


def _period(run: list[PricedHour]) -> tuple[datetime, datetime, float]:
    run_average = round(sum(h.price for h in run) / len(run), 3)
    return run[0].start, run[-1].end, run_average


def cheapest_period(hours: list[PricedHour]) -> tuple[datetime, datetime, float] | None:
    """The consecutive below-average run with the lowest average price.

    Length varies with the day's actual price shape - anywhere from a single
    hour to most of the day - rather than a fixed configured window size.
    Returns (start, end, average_price), or None if there's no priced data.
    """
    day_average = average(hours)
    if day_average is None:
        return None

    runs = _runs(hours, lambda price: price <= day_average)
    if not runs:
        return None

    cheapest_run = min(runs, key=lambda run: sum(h.price for h in run) / len(run))
    return _period(cheapest_run)


def most_expensive_period(hours: list[PricedHour]) -> tuple[datetime, datetime, float] | None:
    """The consecutive above-average run with the highest average price.

    Mirror of cheapest_period(). Returns None if there's no priced data, or
    if every priced hour is at or below the day's average (no above-average
    run exists - e.g. all hours priced identically).
    """
    day_average = average(hours)
    if day_average is None:
        return None

    runs = _runs(hours, lambda price: price > day_average)
    if not runs:
        return None

    priciest_run = max(runs, key=lambda run: sum(h.price for h in run) / len(run))
    return _period(priciest_run)
