"""Binary sensor-platform voor Budget Thuis Dynamic Prices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import BudgetThuisConfigEntry
from .entity import BudgetThuisEntity
from .stats import average, hour_for


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BudgetThuisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet de binary sensors op vanuit een config entry."""
    coordinator = entry.runtime_data

    async_add_entities([BudgetThuisCheapHourBinarySensor(coordinator)])


class BudgetThuisCheapHourBinarySensor(BudgetThuisEntity, BinarySensorEntity):
    """Aan zodra de prijs van het huidige uur op of onder het daggemiddelde ligt.

    Een eenvoudige vuistregel zonder instellingen voor "nu is een goed moment om
    iets te draaien", zodat automatiseringen niet zelf raw_today hoeven uit te
    lezen met een template.
    """

    _attr_translation_key = "cheap_hour"

    @property
    def is_on(self) -> bool | None:
        """Waar als het huidige uur niet duurder is dan het daggemiddelde."""
        hour = hour_for(self.data.today, dt_util.now())
        today_average = average(self.data.today)
        if hour is None or hour.price is None or today_average is None:
            return None
        return hour.price <= today_average
