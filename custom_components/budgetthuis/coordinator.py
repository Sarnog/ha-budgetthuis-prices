"""Data update coordinator for Budget Thuis Dynamic Prices."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BEURSPRIJS_MARKUP,
    CONF_ENERGIEBELASTING,
    CONF_INKOOPVERGOEDING,
    CONF_VAT_PERCENT,
    DEFAULT_BEURSPRIJS_MARKUP,
    DEFAULT_ENERGIEBELASTING,
    DEFAULT_INKOOPVERGOEDING,
    DEFAULT_VAT_PERCENT,
    DOMAIN,
    TARIFF_URL,
    UPDATE_INTERVAL,
)
from .parser import HourPrice, TariffParseError, parse_tariff_days
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


@dataclass
class BudgetThuisData:
    """Priced tariff data for today and (if published) tomorrow."""

    today: list[PricedHour]
    tomorrow: list[PricedHour]

    @property
    def tomorrow_valid(self) -> bool:
        return len(self.tomorrow) > 0


def _contract_config(entry: ConfigEntry) -> ContractConfig:
    options = entry.options
    return ContractConfig(
        inkoopvergoeding=options.get(CONF_INKOOPVERGOEDING, DEFAULT_INKOOPVERGOEDING),
        energiebelasting=options.get(CONF_ENERGIEBELASTING, DEFAULT_ENERGIEBELASTING),
        vat_percent=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
        beursprijs_markup=options.get(CONF_BEURSPRIJS_MARKUP, DEFAULT_BEURSPRIJS_MARKUP),
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


class BudgetThuisCoordinator(DataUpdateCoordinator[BudgetThuisData]):
    """Fetches Budget Thuis dynamic electricity tariffs and prices them for the customer's contract."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry

    async def _async_update_data(self) -> BudgetThuisData:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(TARIFF_URL) as response:
                response.raise_for_status()
                html = await response.text()
        except Exception as err:  # noqa: BLE001 - surfaced uniformly as UpdateFailed
            raise UpdateFailed(f"Error fetching tariff page: {err}") from err

        try:
            by_date = parse_tariff_days(html)
        except TariffParseError as err:
            raise UpdateFailed(str(err)) from err

        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)
        config = _contract_config(self.entry)

        return BudgetThuisData(
            today=_price_hours(by_date.get(today.isoformat(), []), config),
            tomorrow=_price_hours(by_date.get(tomorrow.isoformat(), []), config),
        )
