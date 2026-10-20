"""Home Assistant-level tests for when entity states move to the next price.

Unlike the other test modules these need a real Home Assistant test harness
(pytest-homeassistant-custom-component), so they're skipped when it isn't
installed - plain `pip install -r requirements_test.txt` keeps working.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL

AMSTERDAM = ZoneInfo("Europe/Amsterdam")
DAY_1 = date(2026, 7, 29)
DAY_2 = DAY_1 + timedelta(days=1)
ENERGY_TAX = 0.1
NO_SURCHARGES = {"inkoopvergoeding": 0.0, "vat_percent": 0.0, "beursprijs_markup": 0.0}


def _commodity(day: date, hour: int) -> float:
    """A distinct, easily recognisable beursprijs per (day, hour)."""
    return round((0.5 if day == DAY_2 else 0.0) + hour / 100, 4)


def _ts(day: date, hour: int) -> str:
    """Budget Thuis's naive local timestamp format; hour 24 is the next midnight."""
    return f"{(day + timedelta(days=hour // 24)).isoformat()} {hour % 24:02d}:00:00"


def _tariff(start: str, end: str, commodity: float, tax: float) -> dict:
    return {
        "Start": start,
        "End": end,
        "TotalTariff": {"AmountGross": round((commodity + tax) * 1.21, 5)},
        "Commodity": {"AmountNet": commodity},
        "EnergyTax": {"AmountNet": tax},
    }


def _page(days: list[date]) -> str:
    tariff_days = []
    for day in days:
        electricity = [
            _tariff(_ts(day, h), _ts(day, h + 1), _commodity(day, h), ENERGY_TAX)
            for h in range(24)
        ]
        gas_day_price = 1.0 if day == DAY_1 else 1.2
        gas = [
            # 00:00-06:00 still belongs to the previous gas day.
            _tariff(_ts(day, 0), _ts(day, 6), round(gas_day_price - 0.1, 4), 0.6),
            _tariff(_ts(day, 6), _ts(day, 24), gas_day_price, 0.6),
        ]
        tariff_days.append(
            {"Start": _ts(day, 0), "ElectricityTariffs": electricity, "GasTariffs": gas}
        )
    payload = json.dumps({"props": {"pageProps": {"tariffDays": tariff_days}}})
    return f'<html><script id="__NEXT_DATA__" type="application/json">{payload}</script></html>'


def _local(day: date, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=AMSTERDAM)


@pytest.fixture
async def setup_integration(hass, enable_custom_integrations, aioclient_mock, freezer):
    async def _setup(start: datetime) -> None:
        await hass.config.async_set_time_zone("Europe/Amsterdam")
        freezer.move_to(start)
        aioclient_mock.get(TARIFF_URL, text=_page([DAY_1, DAY_2]))
        entry = MockConfigEntry(domain=DOMAIN, data={}, options=NO_SURCHARGES, unique_id=DOMAIN)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return _setup


async def _move_to(hass, freezer, moment: datetime) -> None:
    freezer.move_to(moment)
    async_fire_time_changed(hass, moment)
    await hass.async_block_till_done()


def _price(hass, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return None if state.state in ("unknown", "unavailable") else float(state.state)


async def test_current_price_switches_on_the_hour_not_on_the_poll(hass, setup_integration, freezer) -> None:
    """Reported bug: started at 14:23, the price only moved on at 15:23."""
    await setup_integration(_local(DAY_1, 14, 23))
    assert _price(hass, "sensor.budget_thuis_dynamic_prices_current_price") == pytest.approx(
        _commodity(DAY_1, 14) + ENERGY_TAX
    )

    await _move_to(hass, freezer, _local(DAY_1, 15, 0, 1))

    assert _price(hass, "sensor.budget_thuis_dynamic_prices_current_price") == pytest.approx(
        _commodity(DAY_1, 15) + ENERGY_TAX
    )
    assert _price(hass, "sensor.budget_thuis_dynamic_prices_next_hour_price") == pytest.approx(
        _commodity(DAY_1, 16) + ENERGY_TAX
    )


async def test_current_price_rolls_over_at_midnight(hass, setup_integration, freezer) -> None:
    """Yesterday's 'tomorrow' must become today at 00:00, not at the next poll."""
    await setup_integration(_local(DAY_1, 23, 40))

    await _move_to(hass, freezer, _local(DAY_2, 0, 0, 1))

    assert _price(hass, "sensor.budget_thuis_dynamic_prices_current_price") == pytest.approx(
        _commodity(DAY_2, 0) + ENERGY_TAX
    )
    # Today's statistics follow the new day too.
    assert _price(hass, "sensor.budget_thuis_dynamic_prices_lowest_price_today") == pytest.approx(
        _commodity(DAY_2, 0) + ENERGY_TAX
    )

