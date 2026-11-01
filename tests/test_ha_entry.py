"""Home Assistant-tests voor het opzetten, mislukken en opruimen van de entry."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.budgetthuis import async_unload_entry
from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL
from tests.ha_helpers import DAY_1, NO_SURCHARGES, local


@pytest.mark.parametrize(
    ("mock_kwargs", "expected_reason"),
    [
        ({"status": 500}, "Fout bij het ophalen van de tarievenpagina"),
        ({"exc": TimeoutError}, "Fout bij het ophalen van de tarievenpagina"),
        ({"text": "<html></html>"}, "Geen __NEXT_DATA__-payload"),
    ],
    ids=["http-fout", "time-out", "pagina-zonder-tarieven"],
)
async def test_failed_fetch_leaves_the_entry_retrying(
    hass, enable_custom_integrations, aioclient_mock, mock_kwargs, expected_reason
) -> None:
    """Mislukt de eerste ronde, dan probeert Home Assistant het later opnieuw."""
    aioclient_mock.get(TARIFF_URL, **mock_kwargs)
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options=NO_SURCHARGES, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert expected_reason in entry.reason


async def test_unload_removes_the_coordinator(hass, setup_integration) -> None:
    """Na ontladen blijft er geen coordinator achter."""
    entry = await setup_integration(local(DAY_1, 14, 23))

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert entry.entry_id not in hass.data[DOMAIN]


async def test_failed_unload_keeps_the_coordinator(hass, setup_integration) -> None:
    """Lukt het ontladen van de platforms niet, dan blijft de entry gewoon werken."""
    entry = await setup_integration(local(DAY_1, 14, 23))

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        assert not await async_unload_entry(hass, entry)

    assert entry.entry_id in hass.data[DOMAIN]
