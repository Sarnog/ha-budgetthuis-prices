"""Gedeelde testopzet: de integratie opzetten tegen een nagebootste tarievenpagina."""

from __future__ import annotations

from datetime import datetime

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL
from tests.ha_helpers import DAY_1, DAY_2, NO_SURCHARGES, page


@pytest.fixture
async def setup_integration(hass, enable_custom_integrations, aioclient_mock, freezer):
    """Zet de integratie op een gegeven moment op, tegen de nagebootste pagina."""

    async def _setup(start: datetime) -> MockConfigEntry:
        await hass.config.async_set_time_zone("Europe/Amsterdam")
        freezer.move_to(start)
        aioclient_mock.get(TARIFF_URL, text=page([DAY_1, DAY_2]))
        entry = MockConfigEntry(
            domain=DOMAIN, data={}, options=NO_SURCHARGES, unique_id=DOMAIN
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup
