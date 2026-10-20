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
from pathlib import Path

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
