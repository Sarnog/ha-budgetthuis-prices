"""Constants for the Budget Thuis Dynamic Prices integration."""
from datetime import timedelta

DOMAIN = "budgetthuis"

TARIFF_URL = "https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven"

NEXT_DATA_PATTERN = (
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
)

# Budget Thuis publishes tomorrow's tariffs in the afternoon, same as the
# day-ahead auction they're derived from. Polling hourly is enough to pick
# that up promptly without hammering the site.
UPDATE_INTERVAL = timedelta(hours=1)

# Entity states are re-evaluated on this wall-clock grid, independent of the
# poll above: the poll's phase depends on when Home Assistant started (e.g.
# 14:23, 15:23, ...), so relying on it alone left the previous hour's price
# showing until the next poll. The page currently has hourly electricity and
# 00:00/06:00 gas boundaries; ticking every quarter hour also covers a future
# move to 15-minute electricity prices. Only the cached data is re-read, no
# extra request is made.
PRICE_TICK_MINUTES = (0, 15, 30, 45)

ATTR_TODAY = "today"
ATTR_TOMORROW = "tomorrow"
ATTR_TOMORROW_VALID = "tomorrow_valid"

CURRENCY_EUR_PER_KWH = "EUR/kWh"
CURRENCY_EUR_PER_M3 = "EUR/m³"

# Contract-pricing options (Home Assistant options flow), mirroring the
# breakdown shown in the Budget Thuis app's own tariff screen: beursprijs
# (live per-hour, already parsed) + energiebelasting with 21% BTW on top,
# plus the inkoopvergoeding, which the app already shows including BTW. energiebelasting is a government tax rate, not a
# Budget Thuis one, and its net amount is already published per hour on the
# tariff page - so it's read live (see pricing.py) rather than configured
# here. "Stroom gemiddeld" in the app is just the resulting average all-in
# price, not a separate input.
CONF_INKOOPVERGOEDING = "inkoopvergoeding"
CONF_VAT_PERCENT = "vat_percent"
CONF_BEURSPRIJS_MARKUP = "beursprijs_markup"
# Gas has its own inkoopvergoeding (EUR/m³, incl. BTW); BTW is shared with electricity.
CONF_GAS_INKOOPVERGOEDING = "gas_inkoopvergoeding"

# Starting points only - match these to your own contract's tariff breakdown
# in the Budget Thuis app, they're not guaranteed accurate for every contract.
# Both inkoopvergoeding defaults are including BTW, as the app shows them.
DEFAULT_INKOOPVERGOEDING = 0.016822
DEFAULT_VAT_PERCENT = 21.0
DEFAULT_BEURSPRIJS_MARKUP = 0.0
DEFAULT_GAS_INKOOPVERGOEDING = 0.06413
