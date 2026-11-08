"""Namen die Home Assistant zelf aanroept en die vulture daarom als ongebruikt ziet.

Alleen het raamwerk gebruikt deze namen (entry points, flows, entiteitseigenschappen);
echt dode code hoort hier niet in, die haal je weg.
"""

# ruff: noqa: B018, F821

# Entry points van de integratie
async_setup_entry
async_unload_entry

# Config- en opties-flow
BudgetThuisConfigFlow
VERSION
async_get_options_flow
async_step_user
async_step_init

# Coordinator en entiteiten
_async_update_data
update_interval
_attr_unique_id
_attr_device_info
native_value
extra_state_attributes
is_on
