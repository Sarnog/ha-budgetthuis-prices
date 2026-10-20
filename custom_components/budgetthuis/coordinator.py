"""Data update coordinator for Budget Thuis Dynamic Prices."""

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
    DEFAULT_BEURSPRIJS_MARKUP,
    DEFAULT_GAS_INKOOPVERGOEDING,
    DEFAULT_INKOOPVERGOEDING,
    DEFAULT_VAT_PERCENT,
    DOMAIN,
    PRICE_TICK_MINUTES,
    TARIFF_URL,
    UPDATE_INTERVAL,
)
from .parser import (
    AMSTERDAM,
    ELECTRICITY,
    GAS,
    HourPrice,
    TariffParseError,
    parse_tariff_days,
)
from .pricing import ContractConfig, calculate_price

_LOGGER = logging.getLogger(__name__)


@dataclass
class PricedHour:
    """One hour's price, both as Budget Thuis's own displayed figure and the
    customer-contract-accurate figure computed from the live beursprijs."""

    start: datetime
    end: datetime
    price: float | None
    site_price: float | None


def _local_today() -> date:
    """Today's date on the tariff page's own (Amsterdam) calendar."""
    return dt_util.now(AMSTERDAM).date()


@dataclass
class BudgetThuisData:
    """Priced tariff data for every day on the page, keyed by ISO date.

    "Today" and "tomorrow" are resolved against the clock whenever they're
    read rather than fixed at fetch time, so at midnight yesterday's
    "tomorrow" becomes today straight away instead of at the next poll.
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
    """Gas: own inkoopvergoeding, shared BTW, no beursprijs correction."""
    options = entry.options
    return ContractConfig(
        inkoopvergoeding=options.get(
            CONF_GAS_INKOOPVERGOEDING, DEFAULT_GAS_INKOOPVERGOEDING
        ),
        vat_percent=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
    )


def _price_hours(hours: list[HourPrice], config: ContractConfig) -> list[PricedHour]:
    return [
        PricedHour(
            start=hour.start,
            end=hour.end,
            price=calculate_price(hour, config),
            site_price=hour.price,
        )
        for hour in hours
    ]


def _price_days(
    by_date: dict[str, list[HourPrice]], config: ContractConfig
) -> dict[str, list[PricedHour]]:
    return {day: _price_hours(hours, config) for day, hours in by_date.items()}


class BudgetThuisCoordinator(DataUpdateCoordinator[BudgetThuisData]):
    """Fetches Budget Thuis dynamic electricity and gas tariffs.

    The tariffs are priced for the customer's own contract (see pricing.py).
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
        """Re-evaluate entity states on every price boundary.

        Returns the unsubscribe callback.

        See PRICE_TICK_MINUTES: the fetch itself stays on its own interval,
        this only lets entities re-read the cached data at the right moment.
        """
        return async_track_time_change(
            self.hass, self._async_price_clock_tick, minute=PRICE_TICK_MINUTES, second=0
        )

    @callback
    def _async_price_clock_tick(self, _now: datetime) -> None:
        if self.data is not None:
            self.async_update_listeners()

    async def _async_update_data(self) -> BudgetThuisData:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(TARIFF_URL) as response:
                response.raise_for_status()
                html = await response.text()
        except Exception as err:  # noqa: BLE001 - surfaced uniformly as UpdateFailed
            raise UpdateFailed(f"Error fetching tariff page: {err}") from err

        try:
            electricity = parse_tariff_days(html, ELECTRICITY)
            gas = parse_tariff_days(html, GAS)
        except TariffParseError as err:
            raise UpdateFailed(str(err)) from err

        return BudgetThuisData(
            electricity=_price_days(electricity, _contract_config(self.entry)),
            gas=_price_days(gas, _gas_contract_config(self.entry)),
        )
