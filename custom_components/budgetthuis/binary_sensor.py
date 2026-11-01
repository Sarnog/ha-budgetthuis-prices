"""Binary sensor-platform voor Budget Thuis Dynamic Prices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import BudgetThuisCoordinator, BudgetThuisData
from .helpers import device_info as get_device_info
from .stats import average, hour_for


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Zet de binary sensors op vanuit een config entry."""
    coordinator: BudgetThuisCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = get_device_info(entry)

    async_add_entities(
        [BudgetThuisCheapHourBinarySensor(coordinator, entry, device_info)]
    )


class BudgetThuisCheapHourBinarySensor(
    CoordinatorEntity[BudgetThuisCoordinator], BinarySensorEntity
):
    """Aan zodra de prijs van het huidige uur op of onder het daggemiddelde ligt.

    Een eenvoudige vuistregel zonder instellingen voor "nu is een goed moment om
    iets te draaien", zodat automatiseringen niet zelf raw_today hoeven uit te
    lezen met een template.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "cheap_hour"
    _attr_icon = "mdi:cash-check"

    def __init__(
        self,
        coordinator: BudgetThuisCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        """Maak de sensor aan onder het gedeelde apparaat."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_cheap_hour"
        self._attr_device_info = device_info

    @property
    def data(self) -> BudgetThuisData:
        """De actuele tariefgegevens van de coordinator."""
        return self.coordinator.data

    @property
    def is_on(self) -> bool | None:
        """Waar als het huidige uur niet duurder is dan het daggemiddelde."""
        hour = hour_for(self.data.today, dt_util.now())
        today_average = average(self.data.today)
        if hour is None or hour.price is None or today_average is None:
            return None
        return hour.price <= today_average
