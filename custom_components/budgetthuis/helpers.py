"""Shared Home Assistant glue for the sensor and binary_sensor platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Budget Thuis Dynamic Prices",
        manufacturer="Budget Thuis",
        entry_type=DeviceEntryType.SERVICE,
    )
