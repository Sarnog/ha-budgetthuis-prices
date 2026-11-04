"""Home Assistant-tests voor wat de sensors tonen en aan andere integraties geven."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.helpers import entity_registry as er

from custom_components.budgetthuis.const import DOMAIN
from tests.ha_helpers import DAY_1, DAY_2, local, move_to

CURRENT_PRICE = "sensor.budget_thuis_dynamic_prices_current_price"
EXPORT_PRICE = "sensor.budget_thuis_dynamic_prices_current_export_price"
CHEAP_HOUR = "binary_sensor.budget_thuis_dynamic_prices_cheap_hour"
CHEAPEST_PERIOD = "sensor.budget_thuis_dynamic_prices_cheapest_period_today"
PRICIEST_PERIOD = "sensor.budget_thuis_dynamic_prices_most_expensive_period_today"


async def test_raw_prices_follow_the_nord_pool_layout(hass, setup_integration) -> None:
    """De Nord Pool-parser van Omnibattery leest {start, end, value} en currency."""
    await setup_integration(local(DAY_1, 14, 23))
    attributes = hass.states.get(CURRENT_PRICE).attributes

    assert attributes["currency"] == "EUR"
    for key in ("raw_today", "raw_tomorrow"):
        entries = attributes[key]
        assert len(entries) == 24
        for entry in entries:
            assert {"start", "end", "value", "price", "site_price"} <= entry.keys()
            assert entry["value"] == entry["price"]


async def test_export_price_follows_the_contract_price_during_saldering(
    hass, setup_integration
) -> None:
    """In 2026 is een teruggeleverde kWh evenveel waard als een afgenomen kWh."""
    await setup_integration(local(DAY_1, 14, 23))
    export = hass.states.get(EXPORT_PRICE)
    current = hass.states.get(CURRENT_PRICE)

    assert export.state == current.state
    assert export.attributes["currency"] == "EUR"
    assert export.attributes["tomorrow_valid"] is True
    for key in ("raw_today", "raw_tomorrow"):
        values = [entry["value"] for entry in export.attributes[key]]
        assert values == [entry["price"] for entry in current.attributes[key]]


async def test_period_sensors_report_the_runs_around_the_average(
    hass, setup_integration
) -> None:
    """De prijzen stijgen de hele dag: de eerste helft is goedkoop, de tweede duur."""
    await setup_integration(local(DAY_1, 14, 23))

    cheapest = hass.states.get(CHEAPEST_PERIOD)
    assert cheapest.state == "00:00 - 12:00"
    assert cheapest.attributes["start"] == local(DAY_1, 0).isoformat()
    assert cheapest.attributes["end"] == local(DAY_1, 12).isoformat()
    assert cheapest.attributes["average_price"] == 0.155

    priciest = hass.states.get(PRICIEST_PERIOD)
    assert priciest.state == "12:00 - 00:00"
    assert priciest.attributes["average_price"] == 0.275


async def test_cheap_hour_is_on_until_the_price_passes_the_average(
    hass, setup_integration, freezer
) -> None:
    """Het gemiddelde is 0,215; uur 11 (0,21) is goedkoop, uur 12 (0,22) niet."""
    await setup_integration(local(DAY_1, 11, 30))
    assert hass.states.get(CHEAP_HOUR).state == "on"

    await move_to(hass, freezer, local(DAY_1, 12, 0, 1))

    assert hass.states.get(CHEAP_HOUR).state == "off"


async def test_sensors_are_unknown_on_a_day_without_prices(
    hass, setup_integration, freezer
) -> None:
    """Zonder prijzen voor vandaag blijven de sensors onbekend, zonder fout."""
    await setup_integration(local(DAY_1, 14, 23))

    await move_to(hass, freezer, local(DAY_2 + timedelta(days=2), 0, 0, 1))

    assert hass.states.get(CURRENT_PRICE).state == "unknown"
    assert hass.states.get(CHEAP_HOUR).state == "unknown"
    period = hass.states.get(CHEAPEST_PERIOD)
    assert period.state == "unknown"
    assert "start" not in period.attributes


async def test_entity_names_follow_the_home_assistant_language(
    hass, setup_integration
) -> None:
    """De namen komen uit de vertalingen; de entity-ID's blijven stabiel per entry."""
    hass.config.language = "nl"
    entry = await setup_integration(local(DAY_1, 14, 23))

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_current_price"
    )
    assert entity_id is not None
    assert (
        hass.states.get(entity_id).name == "Budget Thuis Dynamic Prices Huidige prijs"
    )
