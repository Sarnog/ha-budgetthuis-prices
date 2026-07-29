"""Shared helpers for the sensor and binary_sensor platforms."""
from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import PricedHour


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Budget Thuis Dynamic Prices",
        manufacturer="Budget Thuis",
        entry_type=DeviceEntryType.SERVICE,
    )


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
