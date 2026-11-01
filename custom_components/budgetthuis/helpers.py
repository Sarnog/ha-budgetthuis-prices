"""Gedeelde Home Assistant-code voor de sensor- en binary_sensor-platforms."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Het ene apparaat waaronder alle entiteiten van deze integratie vallen."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Budget Thuis Dynamic Prices",
        manufacturer="Budget Thuis",
        entry_type=DeviceEntryType.SERVICE,
    )
