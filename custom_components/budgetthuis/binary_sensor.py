"""Binary sensor platform for Budget Thuis Dynamic Prices."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    """Set up Budget Thuis binary sensors from a config entry."""
    coordinator: BudgetThuisCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = get_device_info(entry)

    async_add_entities([BudgetThuisCheapHourBinarySensor(coordinator, entry, device_info)])


class BudgetThuisCheapHourBinarySensor(CoordinatorEntity[BudgetThuisCoordinator], BinarySensorEntity):
    """On whenever the current hour's price is at or below today's average.

    A no-configuration heuristic for "is now a good time to run something",
    so automations can be built without templating raw_today themselves.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:cash-check"

    def __init__(self, coordinator: BudgetThuisCoordinator, entry: ConfigEntry, device_info: DeviceInfo) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_cheap_hour"
        self._attr_translation_key = "cheap_hour"
        self._attr_name = "Cheap hour"
        self._attr_device_info = device_info

    @property
    def data(self) -> BudgetThuisData:
        return self.coordinator.data

    @property
    def is_on(self) -> bool | None:
        hour = hour_for(self.data.today, dt_util.now())
        today_average = average(self.data.today)
        if hour is None or hour.price is None or today_average is None:
            return None
        return hour.price <= today_average
