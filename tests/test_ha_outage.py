"""Home Assistant-tests voor een storing bij het ophalen van de tarievenpagina."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.budgetthuis.const import (
    DOMAIN,
    RETRY_INTERVAL,
    TARIFF_URL,
    UPDATE_INTERVAL,
)
from custom_components.budgetthuis.coordinator import BudgetThuisCoordinator
from tests.ha_helpers import (
    DAY_1,
    DAY_2,
    ENERGY_TAX,
    commodity,
    local,
    move_to,
    page,
    state_price,
)

CURRENT_PRICE = "sensor.budget_thuis_dynamic_prices_current_price"


def _coordinator(hass, entry) -> BudgetThuisCoordinator:
    return hass.data[DOMAIN][entry.entry_id]


def _serve(aioclient_mock, **kwargs) -> None:
    """Laat de nagebootste site voortaan dit antwoord geven."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(TARIFF_URL, **kwargs)


async def test_outage_keeps_the_known_prices_and_retries_quickly(
    hass, setup_integration, aioclient_mock, caplog
) -> None:
    """Gemelde storing: één 502 maakte alle sensors een uur lang onbeschikbaar."""
    entry = await setup_integration(local(DAY_1, 17, 32))
    coordinator = _coordinator(hass, entry)
    _serve(aioclient_mock, status=502)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert coordinator.update_interval == RETRY_INTERVAL
    assert state_price(hass, CURRENT_PRICE) == pytest.approx(
        commodity(DAY_1, 17) + ENERGY_TAX
    )
    assert "de laatst bekende prijzen blijven in gebruik" in caplog.text


async def test_recovery_returns_to_the_normal_interval(
    hass, setup_integration, aioclient_mock
) -> None:
    """Na de storing komen nieuwe gegevens binnen en geldt weer het uurinterval."""
    entry = await setup_integration(local(DAY_1, 17, 32))
    coordinator = _coordinator(hass, entry)
    _serve(aioclient_mock, status=502)
    await coordinator.async_refresh()

    _serve(aioclient_mock, text=page([DAY_1]))
    await coordinator.async_refresh()

    assert coordinator.update_interval == UPDATE_INTERVAL
    # Alleen de nieuwe gegevens tellen: daarin staat morgen nog niet.
    assert not coordinator.data.tomorrow_valid


async def test_outage_without_a_price_for_this_hour_makes_sensors_unavailable(
    hass, setup_integration, aioclient_mock, freezer
) -> None:
    """Dekken de bekende prijzen dit uur niet meer, dan is er echt geen prijs."""
    entry = await setup_integration(local(DAY_2, 23, 30))
    coordinator = _coordinator(hass, entry)
    _serve(aioclient_mock, status=502)
    await move_to(hass, freezer, local(DAY_2, 23, 30) + timedelta(hours=1))

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert hass.states.get(CURRENT_PRICE).state == "unavailable"
