"""Home Assistant-tests voor het moment waarop de prijzen doorschuiven."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL
from tests.ha_helpers import (
    DAY_1,
    DAY_2,
    ENERGY_TAX,
    GAS_INKOOPVERGOEDING,
    NO_SURCHARGES,
    commodity,
    local,
    move_to,
    state_price,
)


async def test_current_price_switches_on_the_hour_not_on_the_poll(
    hass, setup_integration, freezer
) -> None:
    """Gemelde bug: gestart om 14:23, de prijs sprong pas om 15:23 door."""
    await setup_integration(local(DAY_1, 14, 23))
    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_current_price"
    ) == pytest.approx(commodity(DAY_1, 14) + ENERGY_TAX)

    await move_to(hass, freezer, local(DAY_1, 15, 0, 1))

    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_current_price"
    ) == pytest.approx(commodity(DAY_1, 15) + ENERGY_TAX)
    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_next_hour_price"
    ) == pytest.approx(commodity(DAY_1, 16) + ENERGY_TAX)


async def test_current_price_rolls_over_at_midnight(
    hass, setup_integration, freezer
) -> None:
    """'Morgen' van gisteren wordt om 00:00 'vandaag', niet bij de volgende ronde."""
    await setup_integration(local(DAY_1, 23, 40))

    await move_to(hass, freezer, local(DAY_2, 0, 0, 1))

    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_current_price"
    ) == pytest.approx(commodity(DAY_2, 0) + ENERGY_TAX)
    # De statistieken van vandaag volgen de nieuwe dag ook.
    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_lowest_price_today"
    ) == pytest.approx(commodity(DAY_2, 0) + ENERGY_TAX)


async def test_gas_price_switches_at_six_with_its_own_inkoopvergoeding(
    hass, setup_integration, freezer
) -> None:
    await setup_integration(local(DAY_1, 5, 37))
    entity_id = "sensor.budget_thuis_dynamic_prices_current_gas_price"
    # 00:00-06:00 heeft nog de prijs van de vorige gasdag.
    assert state_price(hass, entity_id) == pytest.approx(
        0.9 + 0.6 + GAS_INKOOPVERGOEDING
    )
    assert hass.states.get(entity_id).attributes["unit_of_measurement"] == "EUR/m³"

    await move_to(hass, freezer, local(DAY_1, 6, 0, 1))

    assert state_price(hass, entity_id) == pytest.approx(
        1.0 + 0.6 + GAS_INKOOPVERGOEDING
    )
    assert hass.states.get(entity_id).attributes["tomorrow_valid"] is True


async def test_clock_survives_an_options_reload(
    hass, setup_integration, freezer
) -> None:
    """Opties wijzigen laadt de entry opnieuw; die krijgt dan een eigen klok."""
    await setup_integration(local(DAY_1, 5, 10))
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    hass.config_entries.async_update_entry(
        entry, options={**NO_SURCHARGES, "gas_inkoopvergoeding": 0.2}
    )
    await hass.async_block_till_done()
    await move_to(hass, freezer, local(DAY_1, 6, 0, 1))

    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_current_gas_price"
    ) == pytest.approx(1.0 + 0.6 + 0.2)
    assert state_price(
        hass, "sensor.budget_thuis_dynamic_prices_current_price"
    ) == pytest.approx(commodity(DAY_1, 6) + ENERGY_TAX)

    # Na het ontladen mag een latere tik de (verdwenen) coordinator niet meer raken.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await move_to(hass, freezer, local(DAY_1, 7, 0, 1))
    assert (
        hass.states.get("sensor.budget_thuis_dynamic_prices_current_price").state
        == "unavailable"
    )


async def test_autumn_changeover_shows_each_0200_hour(
    hass, enable_custom_integrations, aioclient_mock, freezer
) -> None:
    """Op 2026-10-25 komt 02:00-03:00 twee keer voor; elk uur krijgt een eigen prijs."""
    day = "2026-10-25"
    naive_starts = [0, 1, 2, 2] + list(range(3, 24))
    tariffs = [
        {
            "Start": f"{day} {h:02d}:00:00",
            "End": f"{day} {h + 1:02d}:00:00" if h < 23 else "2026-10-26 00:00:00",
            "TotalTariff": {"AmountGross": float(i)},
            "Commodity": {"AmountNet": float(i)},
            "EnergyTax": {"AmountNet": 0.0},
        }
        for i, h in enumerate(naive_starts)
    ]
    payload = json.dumps(
        {"props": {"pageProps": {"tariffDays": [{"ElectricityTariffs": tariffs}]}}}
    )
    html = f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'

    await hass.config.async_set_time_zone("Europe/Amsterdam")
    summer_0230 = datetime(2026, 10, 25, 0, 30, tzinfo=ZoneInfo("UTC"))
    freezer.move_to(summer_0230)
    aioclient_mock.get(TARIFF_URL, text=html)
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options=NO_SURCHARGES, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    current = "sensor.budget_thuis_dynamic_prices_current_price"
    next_hour = "sensor.budget_thuis_dynamic_prices_next_hour_price"
    assert state_price(hass, current) == 2.0  # 02:30 zomertijd
    assert state_price(hass, next_hour) == 3.0  # 02:30 wintertijd, een echt uur later

    await move_to(hass, freezer, summer_0230 + timedelta(hours=1))  # 02:30 wintertijd

    assert state_price(hass, current) == 3.0
    assert state_price(hass, next_hour) == 4.0
