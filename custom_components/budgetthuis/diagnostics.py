"""Diagnostische gegevens voor Budget Thuis Dynamic Prices.

Via Instellingen → Apparaten & diensten → Budget Thuis → Diagnostiek downloaden
krijg je een overzicht om bij een probleemmelding te voegen. Er zit geen
account of persoonlijke informatie in: alleen de contractinstellingen en welke
dagen de tarievenpagina bevat.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import BudgetThuisConfigEntry
from .models import PricedHour


def _days(by_date: dict[str, list[PricedHour]]) -> dict[str, dict[str, Any]]:
    """Per dag het aantal blokken, de eerste en laatste tijd en ontbrekende prijzen."""
    return {
        day: {
            "blocks": len(hours),
            "first_start": hours[0].start.isoformat(),
            "last_end": hours[-1].end.isoformat(),
            "missing_prices": sum(1 for hour in hours if hour.price is None),
        }
        for day, hours in by_date.items()
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BudgetThuisConfigEntry
) -> dict[str, Any]:
    """Geef de diagnostische gegevens van deze config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "electricity_days": _days(data.electricity),
        "gas_days": _days(data.gas),
    }
