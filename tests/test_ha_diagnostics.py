"""Home Assistant-tests voor de diagnostische gegevens."""

from __future__ import annotations

from custom_components.budgetthuis.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.ha_helpers import DAY_1, DAY_2, NO_SURCHARGES, local


async def test_diagnostics_summarise_the_options_and_the_days(
    hass, setup_integration
) -> None:
    """Diagnostiek toont de instellingen en welke dagen er binnen zijn."""
    entry = await setup_integration(local(DAY_1, 14, 23))

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"] == NO_SURCHARGES
    assert diagnostics["last_update_success"] is True
    assert diagnostics["update_interval"] == "1:00:00"
    days = diagnostics["electricity_days"]
    assert set(days) == {DAY_1.isoformat(), DAY_2.isoformat()}
    assert days[DAY_1.isoformat()]["blocks"] == 24
    assert days[DAY_1.isoformat()]["missing_prices"] == 0
    assert days[DAY_1.isoformat()]["first_start"].startswith(DAY_1.isoformat())
