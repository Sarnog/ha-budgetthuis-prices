"""Test bootstrap.

Registers `custom_components` / `custom_components.budgetthuis` as bare
namespace packages pointing at the real source directories, without ever
executing `custom_components/budgetthuis/__init__.py` (which imports
Home Assistant and isn't needed to test the pure parser module). This lets
`tests/test_parser.py` run with plain pytest, no Home Assistant install
required.

When Home Assistant *is* installed (with pytest-homeassistant-custom-component,
for `tests/test_ha_timing.py`), the real package is left importable instead,
so Home Assistant can load the integration's `__init__.py` normally.
"""

import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def _register_namespace_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


_register_namespace_package("custom_components", REPO_ROOT / "custom_components")
if importlib.util.find_spec("homeassistant") is None:
    _register_namespace_package(
        "custom_components.budgetthuis", REPO_ROOT / "custom_components" / "budgetthuis"
    )


@pytest.fixture
async def setup_integration(hass, enable_custom_integrations, aioclient_mock, freezer):
    """Set the integration up at a given moment against the fake tariff page.

    Only usable when pytest-homeassistant-custom-component is installed (it
    provides hass, aioclient_mock, ...); the imports are local so plain pytest
    can still load this conftest.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.budgetthuis.const import DOMAIN, TARIFF_URL
    from tests.ha_helpers import DAY_1, DAY_2, NO_SURCHARGES, page

    async def _setup(start: datetime) -> None:
        await hass.config.async_set_time_zone("Europe/Amsterdam")
        freezer.move_to(start)
        aioclient_mock.get(TARIFF_URL, text=page([DAY_1, DAY_2]))
        entry = MockConfigEntry(
            domain=DOMAIN, data={}, options=NO_SURCHARGES, unique_id=DOMAIN
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return _setup
