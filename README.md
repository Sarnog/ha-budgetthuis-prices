# Budget Thuis Dynamic Prices

Home Assistant custom integration that exposes [Budget Thuis](https://www.budgetthuis.nl/)'s
dynamic electricity tariffs as sensors, so you can automate around cheap/expensive hours
(battery charging, EV charging, appliance scheduling, etc.).

Reads the public tariff page
[`/energie/klantenservice/actuele-dynamische-tarieven`](https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven)
directly — no account, login, or API key needed. Rather than trust the site's own displayed
all-in price (which reflects Budget Thuis's generic published figure, not necessarily your
specific contract), the integration recomputes the price itself from the live per-hour
beursprijs plus your own contract's inkoopvergoeding, energiebelasting and BTW — the exact
breakdown shown on the tariff screen in the Budget Thuis app. Configure those via
Settings → Devices & Services → Budget Thuis Dynamic Prices → Configure.

## Entities

One device, three sensors:

- **Current price** (`sensor.current_price`) — this hour's customer-contract-accurate price
  (EUR/kWh). Carries the full hourly breakdown as attributes: `raw_today`, `raw_tomorrow`
  (each entry has both `price` — your contract price — and `site_price` — Budget Thuis's own
  displayed figure, for comparison), `tomorrow_valid`, plus average/lowest/highest for both
  days — enough to drive an apexcharts-card style hourly price graph.
- **Next hour price** (`sensor.next_hour_price`) — the upcoming hour's price, useful for
  pre-emptive automations.
- **Today average price** (`sensor.today_average_price`).

Tomorrow's prices are only published by Budget Thuis in the afternoon; until then
`raw_tomorrow` is empty and `tomorrow_valid` is `false`.

## Contract pricing

Configurable via the integration's "Configure" option (Settings → Devices & Services):

| Field | Meaning | Default |
|---|---|---|
| Inkoopvergoeding | Purchasing fee (EUR/kWh) | 0.01682 |
| Energiebelasting | Energy tax (EUR/kWh) | 0.11085 |
| BTW | VAT (%) | 21 |
| Beursprijs adjustment | Optional markup/offset applied to the live beursprijs before the above (EUR/kWh) | 0 |

Price formula: `(beursprijs + beursprijs_adjustment + inkoopvergoeding + energiebelasting) × (1 + btw / 100)`.

**The defaults are a starting point, not guaranteed to match your contract** — read them off
your own tariff breakdown in the Budget Thuis app and enter those instead. Changing these
options reloads the integration and recalculates immediately, no restart needed.

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

`parser.py` (page parsing) and `pricing.py` (the contract price formula) have no Home
Assistant import, so they're covered by plain pytest (`tests/test_parser.py`,
`tests/test_pricing.py`). `coordinator.py`, `config_flow.py`, and `sensor.py` are thin Home
Assistant glue around those two and are best exercised with
`pytest-homeassistant-custom-component` in an actual HA dev environment — not included here.

## Before publishing

- Push this to a real GitHub repo so HACS custom-repository installs and the CI workflows
  in `.github/workflows/` have something to point at.

## Why scrape the page instead of an API?

Budget Thuis doesn't publish a documented public price API. This mirrors the same
`__NEXT_DATA__` extraction already proven out in a companion project's battery-control
Node.js code, which has been fetching this page in production.
