"""Sensor-platform voor Budget Thuis Dynamic Prices."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CURRENCY, CURRENCY_EUR_PER_KWH, CURRENCY_EUR_PER_M3
from .coordinator import BudgetThuisConfigEntry
from .entity import BudgetThuisEntity
from .models import PricedHour
from .stats import (
    average,
    cheapest_period,
    highest,
    hour_for,
    lowest,
    most_expensive_period,
)


def _serialize(hours: list[PricedHour]) -> list[dict[str, Any]]:
    """Maak de uurregels voor de attributen raw_today en raw_tomorrow.

    "value" herhaalt "price", zodat de attributen de indeling van Nord Pool
    (HACS) volgen ({start, end, value}), die prijsgestuurde integraties zoals
    Omnibattery direct lezen. "price" en "site_price" blijven bestaan voor
    bestaande templates en grafieken.
    """
    return [
        {
            "start": h.start.isoformat(),
            "end": h.end.isoformat(),
            "value": h.price,
            "price": h.price,
            "site_price": h.site_price,
        }
        for h in hours
    ]


def _serialize_export(hours: list[PricedHour]) -> list[dict[str, Any]]:
    """De uurregels van de terugleverprijs, in de indeling van Nord Pool.

    Omnibattery leest hiermee de terugleverprijs als aparte prijsbron.
    """
    return [
        {
            "start": h.start.isoformat(),
            "end": h.end.isoformat(),
            "value": h.export_price,
        }
        for h in hours
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BudgetThuisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet de sensors op vanuit een config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            BudgetThuisCurrentPriceSensor(coordinator),
            BudgetThuisNextHourPriceSensor(coordinator),
            BudgetThuisTodayAveragePriceSensor(coordinator),
            BudgetThuisLowestPriceTodaySensor(coordinator),
            BudgetThuisHighestPriceTodaySensor(coordinator),
            BudgetThuisCheapestPeriodTodaySensor(coordinator),
            BudgetThuisMostExpensivePeriodTodaySensor(coordinator),
            BudgetThuisCurrentGasPriceSensor(coordinator),
            BudgetThuisCurrentExportPriceSensor(coordinator),
        ]
    )


class BudgetThuisBaseSensor(BudgetThuisEntity, SensorEntity):
    """Gedeelde opzet voor de numerieke prijssensors in EUR/kWh."""

    _attr_native_unit_of_measurement = CURRENCY_EUR_PER_KWH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3


class BudgetThuisCurrentPriceSensor(BudgetThuisBaseSensor):
    """De prijs van het huidige uur voor het eigen contract."""

    _attr_translation_key = "current_price"
    # De uurlijsten zijn groot en veranderen elke dag; in de recorder zouden
    # ze bij elke toestandswijziging opnieuw worden opgeslagen.
    _unrecorded_attributes = frozenset({"raw_today", "raw_tomorrow"})

    @property
    def native_value(self) -> float | None:
        """De prijs van het uur waarin we nu zitten."""
        hour = hour_for(self.data.today, dt_util.now())
        return hour.price if hour else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """De uurprijzen van vandaag en morgen plus de dagstatistieken."""
        data = self.data
        return {
            "raw_today": _serialize(data.today),
            "raw_tomorrow": _serialize(data.tomorrow),
            "tomorrow_valid": data.tomorrow_valid,
            # Consumenten in Nord Pool-stijl lezen de valuta hieruit.
            "currency": CURRENCY,
            "average_today": average(data.today),
            "lowest_today": lowest(data.today),
            "highest_today": highest(data.today),
            "average_tomorrow": average(data.tomorrow),
            "lowest_tomorrow": lowest(data.tomorrow),
            "highest_tomorrow": highest(data.tomorrow),
        }


class BudgetThuisCurrentExportPriceSensor(BudgetThuisBaseSensor):
    """De opbrengst van een teruggeleverde kWh in het huidige uur.

    Tot en met 2026 de contractprijs (saldering), daarna de beursprijs plus de
    ZonneBonus (zie export_pricing.py).
    """

    _attr_translation_key = "current_export_price"
    # De uurlijsten zijn groot en veranderen elke dag; in de recorder zouden
    # ze bij elke toestandswijziging opnieuw worden opgeslagen.
    _unrecorded_attributes = frozenset({"raw_today", "raw_tomorrow"})

    @property
    def native_value(self) -> float | None:
        """De terugleverprijs van het uur waarin we nu zitten."""
        hour = hour_for(self.data.today, dt_util.now())
        return hour.export_price if hour else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """De terugleverprijzen per uur van vandaag en morgen."""
        data = self.data
        return {
            "raw_today": _serialize_export(data.today),
            "raw_tomorrow": _serialize_export(data.tomorrow),
            "tomorrow_valid": data.tomorrow_valid,
            "currency": CURRENCY,
        }


class BudgetThuisNextHourPriceSensor(BudgetThuisBaseSensor):
    """De prijs van het volgende uur voor het eigen contract.

    Loopt door in de gegevens van morgen zodra die gepubliceerd zijn.
    """

    _attr_translation_key = "next_hour_price"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float | None:
        """De prijs van het uur na dit uur."""
        # utcnow(): een uur optellen bij een lokale tijd is rekenen op de klok,
        # en dat slaat een uur over of herhaalt het bij de zomertijdovergangen.
        next_hour = dt_util.utcnow() + timedelta(hours=1)
        hour = hour_for(self.data.today, next_hour) or hour_for(
            self.data.tomorrow, next_hour
        )
        return hour.price if hour else None


class BudgetThuisTodayAveragePriceSensor(BudgetThuisBaseSensor):
    """De gemiddelde prijs van vandaag voor het eigen contract."""

    _attr_translation_key = "today_average_price"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float | None:
        """Het gemiddelde van de uurprijzen van vandaag."""
        return average(self.data.today)


class BudgetThuisLowestPriceTodaySensor(BudgetThuisBaseSensor):
    """De laagste prijs van vandaag voor het eigen contract."""

    _attr_translation_key = "lowest_price_today"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float | None:
        """De laagste uurprijs van vandaag."""
        return lowest(self.data.today)


class BudgetThuisHighestPriceTodaySensor(BudgetThuisBaseSensor):
    """De hoogste prijs van vandaag voor het eigen contract."""

    _attr_translation_key = "highest_price_today"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float | None:
        """De hoogste uurprijs van vandaag."""
        return highest(self.data.today)


class BudgetThuisCurrentGasPriceSensor(BudgetThuisEntity, SensorEntity):
    """De huidige gasprijs voor het eigen contract (EUR/m³).

    Gas wordt per gasdag geprijsd (06:00-06:00). De pagina splitst die per
    kalenderdag in een blok van 00:00-06:00 en een van 06:00-24:00, dus de prijs
    verandert om 06:00 en niet elk uur. Onbekend als de pagina geen gastarieven
    bevat.
    """

    _attr_translation_key = "current_gas_price"
    # De uurlijsten zijn groot en veranderen elke dag; in de recorder zouden
    # ze bij elke toestandswijziging opnieuw worden opgeslagen.
    _unrecorded_attributes = frozenset({"raw_today", "raw_tomorrow"})
    _attr_native_unit_of_measurement = CURRENCY_EUR_PER_M3
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    @property
    def native_value(self) -> float | None:
        """De prijs van het gasblok waarin we nu zitten."""
        block = hour_for(self.data.gas_today, dt_util.now())
        return block.price if block else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """De gasblokken van vandaag en morgen."""
        data = self.data
        return {
            "raw_today": _serialize(data.gas_today),
            "raw_tomorrow": _serialize(data.gas_tomorrow),
            "tomorrow_valid": data.gas_tomorrow_valid,
        }


class BudgetThuisPeriodSensor(BudgetThuisEntity, SensorEntity):
    """Gedeelde opzet voor de sensors met de goedkoopste en duurste periode.

    De toestand is een leesbaar tijdbereik "UU:MM - UU:MM", geen tijdstempel:
    een tijdstempel wordt als relatieve tijd getoond ("2 uur geleden"), en dat
    zegt niets over een terugkerend blok van de dag. De lengte staat ook niet
    vast, maar volgt uit de reeks uren onder of boven het gemiddelde die de
    prijzen van die dag opleveren.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    # De zoekfunctie van de subklasse, bijvoorbeeld stats.cheapest_period.
    _find_period: Callable[[list[PricedHour]], tuple[datetime, datetime, float] | None]

    @property
    def native_value(self) -> str | None:
        """Het tijdbereik van de periode, of None zonder prijzen."""
        period = self._find_period(self.data.today)
        if period is None:
            return None
        start, end, _average_price = period
        return f"{start:%H:%M} - {end:%H:%M}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Begin, einde en gemiddelde prijs van de periode voor automatiseringen."""
        period = self._find_period(self.data.today)
        if period is None:
            return {}
        start, end, average_price = period
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "average_price": average_price,
        }


class BudgetThuisCheapestPeriodTodaySensor(BudgetThuisPeriodSensor):
    """De goedkoopste aaneengesloten reeks uren onder het gemiddelde van vandaag."""

    _attr_translation_key = "cheapest_period_today"
    _find_period = staticmethod(cheapest_period)


class BudgetThuisMostExpensivePeriodTodaySensor(BudgetThuisPeriodSensor):
    """De duurste aaneengesloten reeks uren boven het gemiddelde van vandaag."""

    _attr_translation_key = "most_expensive_period_today"
    _find_period = staticmethod(most_expensive_period)
