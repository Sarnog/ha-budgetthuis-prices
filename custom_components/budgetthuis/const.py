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

ATTR_TODAY = "today"
ATTR_TOMORROW = "tomorrow"
ATTR_TOMORROW_VALID = "tomorrow_valid"

CURRENCY_EUR_PER_KWH = "EUR/kWh"

# Contract-pricing options (Home Assistant options flow), mirroring the
# breakdown shown in the Budget Thuis app's own tariff screen: beursprijs
# (live per-hour, already parsed) + inkoopvergoeding + energiebelasting,
# then 21% BTW on top. energiebelasting is a government tax rate, not a
# Budget Thuis one, and its net amount is already published per hour on the
# tariff page - so it's read live (see pricing.py) rather than configured
# here. "Stroom gemiddeld" in the app is just the resulting average all-in
# price, not a separate input.
CONF_INKOOPVERGOEDING = "inkoopvergoeding"
CONF_VAT_PERCENT = "vat_percent"
CONF_BEURSPRIJS_MARKUP = "beursprijs_markup"

# Starting points only - match these to your own contract's tariff breakdown
# in the Budget Thuis app, they're not guaranteed accurate for every contract.
DEFAULT_INKOOPVERGOEDING = 0.01682
DEFAULT_VAT_PERCENT = 21.0
DEFAULT_BEURSPRIJS_MARKUP = 0.0
