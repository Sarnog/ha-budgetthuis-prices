"""De integratie Budget Thuis Dynamic Prices."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import BudgetThuisConfigEntry, BudgetThuisCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BudgetThuisConfigEntry) -> bool:
    """Zet de integratie op vanuit een config entry."""
    coordinator = BudgetThuisCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # De coordinator hoort bij de entry zelf (runtime_data) in plaats van in
    # hass.data; Home Assistant ruimt hem dan bij het ontladen vanzelf op.
    entry.runtime_data = coordinator

    entry.async_on_unload(coordinator.async_start_price_clock())
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: BudgetThuisConfigEntry
) -> None:
    """Laad de entry opnieuw als de contractopties veranderen."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: BudgetThuisConfigEntry
) -> bool:
    """Ruim een config entry op."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
