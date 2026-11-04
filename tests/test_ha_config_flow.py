"""Home Assistant-tests voor de config flow en de opties-flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL
from tests.ha_helpers import DAY_1, DAY_2, local, page, state_price


async def _start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_confirms_and_gets_an_entry(
    hass, enable_custom_integrations, aioclient_mock
) -> None:
    """Eén bevestigingsstap, zonder account, maakt de entry aan."""
    aioclient_mock.get(TARIFF_URL, text=page([DAY_1, DAY_2]))

    result = await _start_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Budget Thuis Dynamic Prices"


async def test_second_instance_is_aborted(
    hass, enable_custom_integrations, aioclient_mock
) -> None:
    """Er is maar één entry per Home Assistant."""
    MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN).add_to_hass(hass)

    result = await _start_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_change_the_contract_price(
    hass, setup_integration, freezer
) -> None:
    """Nieuwe contractopties laden de entry opnieuw en rekenen direct door."""
    entry = await setup_integration(local(DAY_1, 14, 23))
    current = "sensor.budget_thuis_dynamic_prices_current_price"
    assert state_price(hass, current) == 0.24  # (0,14 + 0,1), 0% BTW, geen inkoop

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "inkoopvergoeding": 0.02,
            "vat_percent": 21.0,
            "beursprijs_markup": 0.0,
            "gas_inkoopvergoeding": 0.05,
            "zonnebonus_percent": 0.0,
            "zonnebonus_max_beursprijs": 0.20,
            "zonnebonus_from": "2027-01-01",
            "zonnebonus_until": "2027-12-31",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["inkoopvergoeding"] == 0.02
    assert entry.options["zonnebonus_percent"] == 0.0
    assert entry.options["zonnebonus_until"] == "2027-12-31"
    assert state_price(hass, current) == 0.3104  # (0,14 + 0,1) × 1,21 + 0,02
