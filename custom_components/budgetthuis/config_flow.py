"""Config and options flow for Budget Thuis Dynamic Prices."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BEURSPRIJS_MARKUP,
    CONF_ENERGIEBELASTING,
    CONF_INKOOPVERGOEDING,
    CONF_VAT_PERCENT,
    DEFAULT_BEURSPRIJS_MARKUP,
    DEFAULT_ENERGIEBELASTING,
    DEFAULT_INKOOPVERGOEDING,
    DEFAULT_VAT_PERCENT,
    DOMAIN,
)


class BudgetThuisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Budget Thuis Dynamic Prices.

    There's no account to log into - the tariff page is public - so this is a
    single confirmation step that also enforces one entry per HA instance.
    Contract-specific pricing values are set afterwards via the options flow,
    so they can be tuned any time without re-adding the integration.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BudgetThuisOptionsFlow:
        return BudgetThuisOptionsFlow()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Budget Thuis Dynamic Prices", data={})

        return self.async_show_form(step_id="user")


class BudgetThuisOptionsFlow(config_entries.OptionsFlow):
    """Lets the customer match the calculation to their own contract's tariff breakdown."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_INKOOPVERGOEDING,
                    default=options.get(CONF_INKOOPVERGOEDING, DEFAULT_INKOOPVERGOEDING),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ENERGIEBELASTING,
                    default=options.get(CONF_ENERGIEBELASTING, DEFAULT_ENERGIEBELASTING),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_VAT_PERCENT,
                    default=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_BEURSPRIJS_MARKUP,
                    default=options.get(CONF_BEURSPRIJS_MARKUP, DEFAULT_BEURSPRIJS_MARKUP),
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
