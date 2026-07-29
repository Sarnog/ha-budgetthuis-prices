# Budget Thuis Dynamic Prices

Home Assistant custom integration that exposes [Budget Thuis](https://www.budgetthuis.nl/)'s
dynamic electricity tariffs as sensors, so you can automate around cheap/expensive hours
(battery charging, EV charging, appliance scheduling, etc.).

Reads the public tariff page
[`/energie/klantenservice/actuele-dynamische-tarieven`](https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven)
directly — no account, login, or API key needed. Rather than trust the site's own displayed
all-in price (which reflects Budget Thuis's generic published figure, not necessarily your
specific contract), the integration recomputes the price itself from the live per-hour
beursprijs and energiebelasting (both published on the tariff page) plus your own contract's
inkoopvergoeding and BTW — the exact breakdown shown on the tariff screen in the Budget Thuis
app. Configure your inkoopvergoeding via Settings → Devices & Services → Budget Thuis Dynamic
Prices → Configure.

## Entities

One device, seven sensors and a binary sensor:

- **Current price** (`sensor.current_price`) — this hour's customer-contract-accurate price
  (EUR/kWh). Carries the full hourly breakdown as attributes: `raw_today`, `raw_tomorrow`
  (each entry has both `price` — your contract price — and `site_price` — Budget Thuis's own
  displayed figure, for comparison), `tomorrow_valid`, plus average/lowest/highest for both
  days — enough to drive an apexcharts-card style hourly price graph.
- **Next hour price** (`sensor.next_hour_price`) — the upcoming hour's price, useful for
  pre-emptive automations.
- **Today average price** (`sensor.today_average_price`).
- **Lowest price today** (`sensor.lowest_price_today`) / **Highest price today**
  (`sensor.highest_price_today`) — the same figures already in `current_price`'s attributes,
  exposed as their own entities so they're pickable in the UI automation editor (e.g. a
  `numeric_state` trigger comparing `current_price` against `lowest_price_today`) without
  needing a template.
- **Cheapest period today** (`sensor.cheapest_period_today`) / **Most expensive period today**
  (`sensor.most_expensive_period_today`) — timestamp sensors: state is the start of the
  consecutive run of below/above-average hours with the lowest/highest average price that day,
  with `end` and `average_price` as attributes. The run's length isn't configured — it's
  whatever shape that day's prices actually produce, anywhere from a single hour to most of
  the day.
- **Cheap hour** (`binary_sensor.cheap_hour`) — on whenever the current price is at or below
  today's average. A no-configuration building block for "run this when it's cheap"
  automations that doesn't require templating `raw_today` yourself.

Tomorrow's prices are only published by Budget Thuis in the afternoon; until then
`raw_tomorrow` is empty and `tomorrow_valid` is `false` — the period/lowest/highest sensors
only ever look at today's data.

## Contract pricing

Configurable via the integration's "Configure" option (Settings → Devices & Services):

| Field | Meaning | Default |
|---|---|---|
| Inkoopvergoeding | Purchasing fee (EUR/kWh) | 0.01682 |
| BTW | VAT (%) | 21 |
| Beursprijs adjustment | Extra correction on top of the live beursprijs (EUR/kWh) — beursprijs itself is always fetched automatically, this is **not** where you enter it; leave at 0 unless you have a specific reason | 0 |

Price formula: `(beursprijs + beursprijs_adjustment + inkoopvergoeding + energiebelasting) × (1 + btw / 100)`.

Energiebelasting isn't a configurable field — it's a government-set tax rate (the same for
every energy supplier), and its net amount is already published per hour on the tariff page,
so it's read live rather than guessed. Inkoopvergoeding is the one number that's genuinely
specific to your contract and isn't published anywhere public; **the default is a starting
point, not guaranteed to match your contract** — read the real value off your own tariff
breakdown in the Budget Thuis app and enter that instead. Changing these options reloads the
integration and recalculates immediately, no restart needed.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo URL, category "Integration".
2. Install "Budget Thuis Dynamic Prices", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → search "Budget Thuis".

### Manual

Copy `custom_components/budgetthuis` into your Home Assistant `config/custom_components/`
directory and restart.

## Development

```
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest tests/ -v
```

`parser.py` (page parsing), `pricing.py` (the contract price formula), and `stats.py` (today's
average/lowest/highest and the cheapest/most-expensive period search) have no Home Assistant
import, so they're covered by plain pytest (`tests/test_parser.py`, `tests/test_pricing.py`,
`tests/test_stats.py`). `coordinator.py`, `config_flow.py`, `sensor.py`, `binary_sensor.py`,
and `helpers.py` are thin Home Assistant glue around those and are best exercised with
`pytest-homeassistant-custom-component` in an actual HA dev environment — not included here.

## Before publishing

- Push this to a real GitHub repo so HACS custom-repository installs and the CI workflows
  in `.github/workflows/` have something to point at.

## Why scrape the page instead of an API?

Budget Thuis doesn't publish a documented public price API. This mirrors the same
`__NEXT_DATA__` extraction already proven out in a companion project's battery-control
Node.js code, which has been fetching this page in production.
