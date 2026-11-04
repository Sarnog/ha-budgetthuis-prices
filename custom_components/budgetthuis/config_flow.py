"""Config- en opties-flow voor Budget Thuis Dynamic Prices."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import DateSelector

from .const import (
    CONF_BEURSPRIJS_MARKUP,
    CONF_GAS_INKOOPVERGOEDING,
    CONF_INKOOPVERGOEDING,
    CONF_VAT_PERCENT,
    CONF_ZONNEBONUS_FROM,
    CONF_ZONNEBONUS_MAX_BEURSPRIJS,
    CONF_ZONNEBONUS_PERCENT,
    CONF_ZONNEBONUS_UNTIL,
    DEFAULT_BEURSPRIJS_MARKUP,
    DEFAULT_GAS_INKOOPVERGOEDING,
    DEFAULT_INKOOPVERGOEDING,
    DEFAULT_VAT_PERCENT,
    DEFAULT_ZONNEBONUS_FROM,
    DEFAULT_ZONNEBONUS_MAX_BEURSPRIJS,
    DEFAULT_ZONNEBONUS_PERCENT,
    DOMAIN,
)


class BudgetThuisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow voor Budget Thuis Dynamic Prices.

    Er is geen account om in te loggen, want de tarievenpagina is openbaar. Het
    is dus één bevestigingsstap, die ook afdwingt dat er maar één entry per
    Home Assistant is. De contractprijzen stel je daarna in via de opties-flow,
    zodat ze altijd aan te passen zijn zonder de integratie opnieuw toe te voegen.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BudgetThuisOptionsFlow:
        """Geef de opties-flow voor deze entry."""
        return BudgetThuisOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bevestig het toevoegen; één entry per installatie."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Budget Thuis Dynamic Prices", data={})

        return self.async_show_form(step_id="user")


class BudgetThuisOptionsFlow(config_entries.OptionsFlow):
    """Laat de klant de berekening afstemmen op de tariefopbouw van het contract."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Toon of bewaar de contractprijzen."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_INKOOPVERGOEDING,
                    default=options.get(
                        CONF_INKOOPVERGOEDING, DEFAULT_INKOOPVERGOEDING
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_VAT_PERCENT,
                    default=options.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_BEURSPRIJS_MARKUP,
                    default=options.get(
                        CONF_BEURSPRIJS_MARKUP, DEFAULT_BEURSPRIJS_MARKUP
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_GAS_INKOOPVERGOEDING,
                    default=options.get(
                        CONF_GAS_INKOOPVERGOEDING, DEFAULT_GAS_INKOOPVERGOEDING
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_ZONNEBONUS_PERCENT,
                    default=options.get(
                        CONF_ZONNEBONUS_PERCENT, DEFAULT_ZONNEBONUS_PERCENT
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional(
                    CONF_ZONNEBONUS_MAX_BEURSPRIJS,
                    default=options.get(
                        CONF_ZONNEBONUS_MAX_BEURSPRIJS,
                        DEFAULT_ZONNEBONUS_MAX_BEURSPRIJS,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional(
                    CONF_ZONNEBONUS_FROM,
                    default=options.get(CONF_ZONNEBONUS_FROM, DEFAULT_ZONNEBONUS_FROM),
                ): DateSelector(),
                # Geen default maar een voorgestelde waarde: zo kan de einddatum
                # weer leeggemaakt worden (geen einde).
                vol.Optional(
                    CONF_ZONNEBONUS_UNTIL,
                    description={"suggested_value": options.get(CONF_ZONNEBONUS_UNTIL)},
                ): DateSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
