"""Pure parsing logic for the Budget Thuis tariff page.

Deliberately free of any Home Assistant import so it can be unit tested with
plain pytest, independent of whatever HA dev environment is available.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
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


def _parse_local_timestamp(value: str) -> datetime:
    """Parse a Budget Thuis timestamp (naive, Europe/Amsterdam local) into an aware datetime."""
    return datetime.fromisoformat(value).replace(tzinfo=AMSTERDAM)


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
        for tariff in tariffs:
            start_raw = tariff.get("Start")
            end_raw = tariff.get("End")
            total = tariff.get("TotalTariff") or {}
            price = total.get("AmountGross")
            if start_raw is None or end_raw is None or price is None:
                continue

            hours.append(
                HourPrice(
                    start=_parse_local_timestamp(start_raw),
                    end=_parse_local_timestamp(end_raw),
                    price=float(price),
                    commodity_net=(tariff.get("Commodity") or {}).get("AmountNet"),
                    energy_tax_net=(tariff.get("EnergyTax") or {}).get("AmountNet"),
                )
            )

        if hours:
            hours.sort(key=lambda h: h.start)
            by_date[hours[0].start.date().isoformat()] = hours

    return by_date
