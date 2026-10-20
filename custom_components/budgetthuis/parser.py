"""Pure parsing logic for the Budget Thuis tariff page.

Deliberately free of any Home Assistant import so it can be unit tested with
plain pytest, independent of whatever HA dev environment is available.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

from .const import NEXT_DATA_PATTERN

AMSTERDAM = ZoneInfo("Europe/Amsterdam")

# Keys of the per-day tariff lists in the page payload. Electricity comes in
# hourly blocks; gas in two blocks per calendar day (00:00-06:00, still the
# previous gas day's price, and 06:00-24:00), since a gas day starts at 06:00.
ELECTRICITY = "ElectricityTariffs"
GAS = "GasTariffs"


class TariffParseError(Exception):
    """Raised when the tariff page can't be parsed into hourly prices."""


@dataclass
class HourPrice:
    """A single tariff block: one hour for electricity, a part of the day for gas."""

    start: datetime
    end: datetime
    price: float
    commodity_net: float | None
    energy_tax_net: float | None


# Daylight saving time: the page's timestamps are naive Amsterdam wall-clock
# times. On the autumn changeover 02:00-03:00 happens twice, on the spring one
# it doesn't happen at all, so a naive timestamp alone can't always tell which
# real moment is meant. The helpers below resolve that, and all comparisons
# elsewhere use absolute instants (see stats.hour_for).


def _localize(naive: datetime, fold: int) -> datetime:
    """Attach Amsterdam time and normalise via UTC.

    The round trip gives the repeated autumn hour its proper fold, and moves a
    spring-forward time that doesn't exist (02:xx) onto the real instant.
    """
    aware = naive.replace(tzinfo=AMSTERDAM, fold=fold)
    return aware.astimezone(UTC).astimezone(AMSTERDAM)


def _parse_start(value: str, seen: set[datetime]) -> datetime:
    """Parse a block start; a naive wall-clock time seen before is the repeat.

    Blocks are listed in order, so the second "02:00" on the autumn changeover
    day is the winter time hour (fold=1). Timestamps that carry their own UTC
    offset are taken as-is.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(AMSTERDAM)
    fold = 1 if parsed in seen else 0
    seen.add(parsed)
    return _localize(parsed, fold)


def _parse_end(value: str, start: datetime) -> datetime:
    """Parse a block end, taking the repeated hour's later instant if needed."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(AMSTERDAM)
    end = _localize(parsed, 0)
    if end.timestamp() <= start.timestamp():
        end = _localize(parsed, 1)
    return end


def _clip_overlaps(blocks: list[HourPrice]) -> None:
    """End each block no later than the next one starts.

    A naive end can't distinguish the two 02:00-03:00 hours either, so the
    first of them would otherwise run on into the second.
    """
    for block, following in pairwise(blocks):
        if block.end.timestamp() > following.start.timestamp():
            block.end = following.start


def parse_tariff_days(html: str, tariff_key: str = ELECTRICITY) -> dict[str, list[HourPrice]]:
    """Parse the __NEXT_DATA__ payload embedded in the tariff page into per-day prices.

    tariff_key selects the commodity (ELECTRICITY or GAS). A page without any
    entries for that commodity yields an empty dict, not an error.

    Mirrors the extraction already proven in the arandu project's
    node/src/providers/price-provider.js `fetchBudgetThuis`.
    """
    match = re.search(NEXT_DATA_PATTERN, html, re.DOTALL)
    if not match:
        raise TariffParseError("No __NEXT_DATA__ payload found on tariff page")

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as err:
        raise TariffParseError(f"Malformed __NEXT_DATA__ JSON: {err}") from err

    tariff_days = (payload.get("props") or {}).get("pageProps", {}).get("tariffDays")
    if not isinstance(tariff_days, list):
        raise TariffParseError("No tariffDays in tariff page payload")

    by_date: dict[str, list[HourPrice]] = {}
    for day in tariff_days:
        tariffs = day.get(tariff_key)
        if not isinstance(tariffs, list):
            continue

        hours: list[HourPrice] = []
        seen: set[datetime] = set()
        for tariff in tariffs:
            start_raw = tariff.get("Start")
            end_raw = tariff.get("End")
            if start_raw is None or end_raw is None:
                continue
            # Before the price check, so a skipped first 02:00 block still
            # marks the next 02:00 as the repeated hour.
            start = _parse_start(start_raw, seen)
            total = tariff.get("TotalTariff") or {}
            price = total.get("AmountGross")
            if price is None:
                continue

            hours.append(
                HourPrice(
                    start=start,
                    end=_parse_end(end_raw, start),
                    price=float(price),
                    commodity_net=(tariff.get("Commodity") or {}).get("AmountNet"),
                    energy_tax_net=(tariff.get("EnergyTax") or {}).get("AmountNet"),
                )
            )

        if hours:
            hours.sort(key=lambda h: h.start.timestamp())
            _clip_overlaps(hours)
            by_date[hours[0].start.date().isoformat()] = hours

    return by_date
