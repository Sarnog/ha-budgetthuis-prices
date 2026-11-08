"""Coordinator die de tarieven van Budget Thuis ophaalt en prijst."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BEURSPRIJS_MARKUP,
    CONF_GAS_INKOOPVERGOEDING,
    CONF_INKOOPVERGOEDING,
    CONF_VAT_PERCENT,
    CONF_ZONNEBONUS_FROM,
    CONF_ZONNEBONUS_MAX_BEURSPRIJS,
    CONF_ZONNEBONUS_PERCENT,
    CONF_ZONNEBONUS_UNTIL,
    DEFAULT_BEURSPRIJS_MARKUP,
    DEFAULT_GAS_INKOOPVERGOEDING,
    DEFAULT_INKOOPVERGOEDING,
    DEFAULT_VAT_PERCENT,
    DEFAULT_ZONNEBONUS_FROM,
    DEFAULT_ZONNEBONUS_MAX_BEURSPRIJS,
    DEFAULT_ZONNEBONUS_PERCENT,
    DOMAIN,
    PRICE_TICK_MINUTES,
    RETRY_INTERVAL,
    TARIFF_URL,
    UPDATE_INTERVAL,
)
from .export_pricing import ExportConfig, Location, calculate_export_price
from .parser import (
    AMSTERDAM,
    ELECTRICITY,
    GAS,
    HourPrice,
    TariffParseError,
    parse_tariff_days,
)
from .pricing import ContractConfig, calculate_price
from .stats import hour_for

_LOGGER = logging.getLogger(__name__)


@dataclass
class PricedHour:
    """De prijs van één blok: de prijs voor het eigen contract (price), de
    all-in prijs die Budget Thuis zelf toont (site_price) en, alleen bij stroom,
    de opbrengst van een teruggeleverde kWh (export_price)."""

    start: datetime
    end: datetime
    price: float | None
    site_price: float | None
    export_price: float | None = None


def _local_today() -> date:
    """De datum van vandaag op de (Amsterdamse) kalender van de tarievenpagina."""
    return dt_util.now(AMSTERDAM).date()


@dataclass
class BudgetThuisData:
    """Geprijsde tariefgegevens voor elke dag op de pagina, per ISO-datum.

    "Vandaag" en "morgen" worden bij het uitlezen aan de klok gekoppeld in
    plaats van bij het ophalen, zodat "morgen" van gisteren om middernacht
    meteen "vandaag" wordt en niet pas bij de volgende ophaalronde.
    """

    electricity: dict[str, list[PricedHour]]
    gas: dict[str, list[PricedHour]]

    @staticmethod
    def _day(by_date: dict[str, list[PricedHour]], offset: int) -> list[PricedHour]:
        return by_date.get((_local_today() + timedelta(days=offset)).isoformat(), [])

    @property
    def today(self) -> list[PricedHour]:
        return self._day(self.electricity, 0)

    @property
    def tomorrow(self) -> list[PricedHour]:
        return self._day(self.electricity, 1)

    @property
    def tomorrow_valid(self) -> bool:
        return len(self.tomorrow) > 0

    @property
    def gas_today(self) -> list[PricedHour]:
        return self._day(self.gas, 0)

    @property
    def gas_tomorrow(self) -> list[PricedHour]:
        return self._day(self.gas, 1)

    @property
    def gas_tomorrow_valid(self) -> bool:
        return len(self.gas_tomorrow) > 0


def _contract_config(entry: ConfigEntry) -> ContractConfig:
    options = entry.options
    return ContractConfig(
        inkoopvergoeding=options.get(CONF_INKOOPVERGOEDING, DEFAULT_INKOOPVERGOEDING),
        vat_percent=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
        beursprijs_markup=options.get(
            CONF_BEURSPRIJS_MARKUP, DEFAULT_BEURSPRIJS_MARKUP
        ),
    )


def _gas_contract_config(entry: ConfigEntry) -> ContractConfig:
    """Gas: eigen inkoopvergoeding, gedeelde BTW, geen beursprijscorrectie."""
    options = entry.options
    return ContractConfig(
        inkoopvergoeding=options.get(
            CONF_GAS_INKOOPVERGOEDING, DEFAULT_GAS_INKOOPVERGOEDING
        ),
        vat_percent=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
    )


def _export_config(hass: HomeAssistant, entry: ConfigEntry) -> ExportConfig:
    """De ZonneBonus-opties, op de locatie van Home Assistant.

    De datums staan als "JJJJ-MM-DD" in de opties (datumkiezer); een lege
    einddatum betekent dat de bonus doorloopt.
    """
    options = entry.options
    until = options.get(CONF_ZONNEBONUS_UNTIL)
    return ExportConfig(
        location=Location(hass.config.latitude, hass.config.longitude),
        bonus_percent=options.get(CONF_ZONNEBONUS_PERCENT, DEFAULT_ZONNEBONUS_PERCENT),
        bonus_max_beursprijs=options.get(
            CONF_ZONNEBONUS_MAX_BEURSPRIJS, DEFAULT_ZONNEBONUS_MAX_BEURSPRIJS
        ),
        bonus_from=date.fromisoformat(
            options.get(CONF_ZONNEBONUS_FROM, DEFAULT_ZONNEBONUS_FROM)
        ),
        bonus_until=date.fromisoformat(until) if until else None,
    )


def _price_hours(
    hours: list[HourPrice], config: ContractConfig, export: ExportConfig | None
) -> list[PricedHour]:
    """Prijs de blokken; met export-instellingen ook de terugleverprijs (stroom)."""
    priced_hours = []
    for hour in hours:
        price = calculate_price(hour, config)
        priced_hours.append(
            PricedHour(
                start=hour.start,
                end=hour.end,
                price=price,
                site_price=hour.price,
                export_price=(
                    None
                    if export is None
                    else calculate_export_price(hour, price, export)
                ),
            )
        )
    return priced_hours


def _price_days(
    by_date: dict[str, list[HourPrice]],
    config: ContractConfig,
    export: ExportConfig | None = None,
) -> dict[str, list[PricedHour]]:
    return {day: _price_hours(hours, config, export) for day, hours in by_date.items()}


class BudgetThuisCoordinator(DataUpdateCoordinator[BudgetThuisData]):
    """Haalt de dynamische stroom- en gastarieven van Budget Thuis op.

    De tarieven worden geprijsd voor het eigen contract (zie pricing.py).
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry

    @callback
    def async_start_price_clock(self) -> CALLBACK_TYPE:
        """Bepaal de entiteitstoestanden opnieuw op elke prijsgrens.

        Geeft de callback terug om dit weer te stoppen.

        Zie PRICE_TICK_MINUTES: het ophalen houdt zijn eigen interval, dit laat
        de entiteiten alleen op het juiste moment de opgeslagen gegevens lezen.
        """
        return async_track_time_change(
            self.hass, self._async_price_clock_tick, minute=PRICE_TICK_MINUTES, second=0
        )

    @callback
    def _async_price_clock_tick(self, _now: datetime) -> None:
        # De klok start pas na de eerste geslaagde ophaalronde, dus er zijn
        # altijd gegevens om opnieuw te lezen.
        self.async_update_listeners()

    async def _async_update_data(self) -> BudgetThuisData:
        """Haal de tarieven op; bij een storing blijven de bekende prijzen staan.

        De pagina bevat de prijzen van vandaag (en vanaf de middag van morgen),
        dus een mislukte ronde hoeft de sensors niet onbeschikbaar te maken
        zolang er al een prijs voor het huidige uur is. Prijsgestuurde
        integraties zoals Omnibattery stoppen anders met ontladen. Tijdens de
        storing wordt het elke RETRY_INTERVAL opnieuw geprobeerd.
        """
        try:
            data = await self._async_fetch_data()
        except UpdateFailed as err:
            if self.data is None or hour_for(self.data.today, dt_util.now()) is None:
                raise
            _LOGGER.warning("%s; de laatst bekende prijzen blijven in gebruik", err)
            self.update_interval = RETRY_INTERVAL
            return self.data
        self.update_interval = UPDATE_INTERVAL
        return data

    async def _async_fetch_data(self) -> BudgetThuisData:
        """Lees de tarievenpagina en prijs elke dag voor het eigen contract."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(TARIFF_URL) as response:
                response.raise_for_status()
                html = await response.text()
        except Exception as err:  # noqa: BLE001 - elke fout wordt als UpdateFailed gemeld
            raise UpdateFailed(
                f"Fout bij het ophalen van de tarievenpagina: {err}"
            ) from err

        try:
            electricity = parse_tariff_days(html, ELECTRICITY)
            gas = parse_tariff_days(html, GAS)
        except TariffParseError as err:
            raise UpdateFailed(str(err)) from err

        return BudgetThuisData(
            electricity=_price_days(
                electricity,
                _contract_config(self.entry),
                _export_config(self.hass, self.entry),
            ),
            gas=_price_days(gas, _gas_contract_config(self.entry)),
        )
