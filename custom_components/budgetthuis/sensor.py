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

from .const import CURRENCY_EUR_PER_KWH, CURRENCY_EUR_PER_M3, DOMAIN
from .coordinator import BudgetThuisCoordinator, BudgetThuisData, PricedHour
from .helpers import device_info as get_device_info
from .stats import average, cheapest_period, highest, hour_for, lowest, most_expensive_period


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
            BudgetThuisCheapestPeriodTodaySensor(coordinator, entry, device_info),
            BudgetThuisMostExpensivePeriodTodaySensor(coordinator, entry, device_info),
            BudgetThuisCurrentGasPriceSensor(coordinator, entry, device_info),
        ]
    )


class BudgetThuisEntity(CoordinatorEntity[BudgetThuisCoordinator]):
    """Shared setup for all Budget Thuis entities."""

    _attr_has_entity_name = True

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


class BudgetThuisBaseSensor(BudgetThuisEntity, SensorEntity):
    """Shared setup for the numeric EUR/kWh price sensors."""

    _attr_native_unit_of_measurement = CURRENCY_EUR_PER_KWH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"
    _attr_suggested_display_precision = 3


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


class BudgetThuisCurrentGasPriceSensor(BudgetThuisEntity, SensorEntity):
    """Current customer-contract-accurate gas price (EUR/m³).

    Gas is priced per gas day (06:00-06:00), which the page splits into a
    00:00-06:00 and a 06:00-24:00 block per calendar day - so this changes
    at 06:00, not every hour. Unknown when the page carries no gas tariffs.
    """

    _attr_native_unit_of_measurement = CURRENCY_EUR_PER_M3
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:fire"
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "current_gas_price", "Current gas price")

    @property
    def native_value(self) -> float | None:
        block = hour_for(self.data.gas_today, dt_util.now())
        return block.price if block else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.data
        return {
            "raw_today": _serialize(data.gas_today),
            "raw_tomorrow": _serialize(data.gas_tomorrow),
            "tomorrow_valid": data.gas_tomorrow_valid,
        }


class BudgetThuisPeriodSensor(BudgetThuisEntity, SensorEntity):
    """Shared setup for the cheapest/most-expensive contiguous-period sensors.

    State is a human-readable "HH:MM - HH:MM" time range, not a timestamp -
    a timestamp device class would render as relative time ("2 hours ago"),
    which is meaningless for a recurring block of the day. Its length isn't
    fixed either; it's whatever consecutive run of below/above-average hours
    the day's prices produce.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def _period(self) -> tuple | None:
        raise NotImplementedError

    @property
    def native_value(self) -> str | None:
        period = self._period()
        if period is None:
            return None
        start, end, _average_price = period
        return f"{start:%H:%M} - {end:%H:%M}"

    @property
    def extra_state_attributes(self) -> dict:
        period = self._period()
        if period is None:
            return {}
        start, end, average_price = period
        return {"start": start.isoformat(), "end": end.isoformat(), "average_price": average_price}


class BudgetThuisCheapestPeriodTodaySensor(BudgetThuisPeriodSensor):
    """Start of today's cheapest consecutive run of below-average hours."""

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(coordinator, entry, device_info, "cheapest_period_today", "Cheapest period today")

    def _period(self):
        return cheapest_period(self.data.today)


class BudgetThuisMostExpensivePeriodTodaySensor(BudgetThuisPeriodSensor):
    """Start of today's most expensive consecutive run of above-average hours."""

    def __init__(self, coordinator, entry, device_info) -> None:
        super().__init__(
            coordinator, entry, device_info, "most_expensive_period_today", "Most expensive period today"
        )

    def _period(self):
        return most_expensive_period(self.data.today)
