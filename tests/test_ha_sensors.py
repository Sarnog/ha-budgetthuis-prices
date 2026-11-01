"""Home Assistant-level tests for what the sensors expose to other integrations.

Like test_ha_timing.py these need pytest-homeassistant-custom-component and
are skipped without it.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from tests.ha_helpers import DAY_1, local


async def test_raw_prices_follow_the_nord_pool_layout(hass, setup_integration) -> None:
    """Omnibattery's Nord Pool parser reads {start, end, value} + currency."""
    await setup_integration(local(DAY_1, 14, 23))
    attributes = hass.states.get(
        "sensor.budget_thuis_dynamic_prices_current_price"
    ).attributes

    assert attributes["currency"] == "EUR"
    for key in ("raw_today", "raw_tomorrow"):
        entries = attributes[key]
        assert len(entries) == 24
        for entry in entries:
            assert {"start", "end", "value", "price", "site_price"} <= entry.keys()
            assert entry["value"] == entry["price"]
