"""Sensor platform for Budget Thuis Dynamic Prices."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CURRENCY_EUR_PER_KWH, DOMAIN
from .coordinator import BudgetThuisCoordinator, BudgetThuisData, PricedHour
from .helpers import average, device_info as get_device_info, highest, hour_for, lowest


def _serialize(hours: list[PricedHour]) -> list[dict]:
    return [
        {
            "start": h.start.isoformat(),
            "end": h.end.isoformat(),
            "price": h.price,
            "site_price": h.site_price,
        }
        for h in hours
    ]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Budget Thuis sensors from a config entry."""
    coordinator: BudgetThuisCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = get_device_info(entry)

    async_add_entities(
        [
            BudgetThuisCurrentPriceSensor(coordinator, entry, device_info),
            BudgetThuisNextHourPriceSensor(coordinator, entry, device_info),
            BudgetThuisTodayAveragePriceSensor(coordinator, entry, device_info),
            BudgetThuisLowestPriceTodaySensor(coordinator, entry, device_info),
            BudgetThuisHighestPriceTodaySensor(coordinator, entry, device_info),
        ]
    )


class BudgetThuisBaseSensor(CoordinatorEntity[BudgetThuisCoordinator], SensorEntity):
    """Shared setup for all Budget Thuis price sensors."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = CURRENCY_EUR_PER_KWH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: BudgetThuisCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_device_info = device_info

    @property
    def data(self) -> BudgetThuisData:
        return self.coordinator.data


class BudgetThuisCurrentPriceSensor(BudgetThuisBaseSensor):
    """Current hour's customer-contract-accurate electricity price."""

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "current_price", "Current price")

    @property
    def native_value(self) -> float | None:
        hour = hour_for(self.data.today, dt_util.now())
        return hour.price if hour else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.data
        return {
            "raw_today": _serialize(data.today),
            "raw_tomorrow": _serialize(data.tomorrow),
            "tomorrow_valid": data.tomorrow_valid,
            "average_today": average(data.today),
            "lowest_today": lowest(data.today),
            "highest_today": highest(data.today),
            "average_tomorrow": average(data.tomorrow),
            "lowest_tomorrow": lowest(data.tomorrow),
            "highest_tomorrow": highest(data.tomorrow),
        }


class BudgetThuisNextHourPriceSensor(BudgetThuisBaseSensor):
    """Next hour's customer-contract-accurate price, spanning into tomorrow's data once published."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "next_hour_price", "Next hour price")

    @property
    def native_value(self) -> float | None:
        next_hour = dt_util.now() + timedelta(hours=1)
        hour = hour_for(self.data.today, next_hour) or hour_for(self.data.tomorrow, next_hour)
        return hour.price if hour else None


class BudgetThuisTodayAveragePriceSensor(BudgetThuisBaseSensor):
    """Today's average customer-contract-accurate price."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "today_average_price", "Today average price")

    @property
    def native_value(self) -> float | None:
        return average(self.data.today)


class BudgetThuisLowestPriceTodaySensor(BudgetThuisBaseSensor):
    """Today's lowest customer-contract-accurate price."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "lowest_price_today", "Lowest price today")

    @property
    def native_value(self) -> float | None:
        return lowest(self.data.today)


class BudgetThuisHighestPriceTodaySensor(BudgetThuisBaseSensor):
    """Today's highest customer-contract-accurate price."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "highest_price_today", "Highest price today")

    @property
    def native_value(self) -> float | None:
        return highest(self.data.today)
