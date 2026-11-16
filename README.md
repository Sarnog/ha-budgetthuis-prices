# Budget Thuis Dynamic Prices

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Release](https://img.shields.io/github/v/release/Sarnog/ha-budgetthuis-prices)](https://github.com/Sarnog/ha-budgetthuis-prices/releases)
[![Tests](https://github.com/Sarnog/ha-budgetthuis-prices/actions/workflows/tests.yml/badge.svg)](https://github.com/Sarnog/ha-budgetthuis-prices/actions/workflows/tests.yml)

**[English](#english)** · **[Nederlands](#nederlands)**

---

## English

A Home Assistant integration that brings the dynamic electricity and gas prices of [Budget Thuis](https://www.budgetthuis.nl/) into Home Assistant, so you can automate around cheap and expensive hours: charge a home battery or an EV, or run appliances when power is cheapest.

The integration reads Budget Thuis's public [tariff page](https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven). No account or API key is needed. It calculates the price for *your* contract itself: the hourly market price (*beursprijs*) and energy tax (*energiebelasting*) from the page, plus VAT and your own purchasing fee (*inkoopvergoeding*). The all-in price shown on the website is not used, because it does not include your personal purchasing fee.

### Installation

**Via HACS**

1. In HACS, open the menu (⋮) and choose **Custom repositories**.
2. Add `https://github.com/Sarnog/ha-budgetthuis-prices` with the type **Integration**.
3. Search for **Budget Thuis Dynamic Prices**, download it and restart Home Assistant.

**Manually**

Copy the `custom_components/budgetthuis` folder into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

**Add the integration**

Go to **Settings → Devices & services → Add integration** and search for **Budget Thuis**. There is nothing to fill in; one instance per Home Assistant installation is all you need.

### Configuration

Go to **Settings → Devices & services → Budget Thuis Dynamic Prices → Configure**.

| Option | Meaning | Default |
|---|---|---|
| Inkoopvergoeding electricity | EUR/kWh, **including VAT**, exactly as the Budget Thuis app shows it | 0.016822 |
| Inkoopvergoeding gas | EUR/m³, **including VAT** | 0.06413 |
| VAT (BTW) | Percentage | 21 |
| Extra market price correction | EUR/kWh, for special cases only | 0 |
| ZonneBonus | Percentage on top of the export price from 2027; 0 turns it off | 30 |
| ZonneBonus: maximum market price | EUR/kWh | 0.20 |
| ZonneBonus from / until | Dates; leave the end date empty for no end | 1 Jan 2027 / empty |

The defaults are only a starting point and may not match your contract. Copy the amounts from the tariff breakdown in the Budget Thuis app or on mijn.budgetthuis.nl. Everything is recalculated as soon as you save.

The price is calculated as:

```
price = (market price + correction + energy tax) × (1 + VAT / 100) + purchasing fee
```

### Entities

| Entity | Description |
|---|---|
| Current price | This hour's price in EUR/kWh, with today's and tomorrow's hourly prices as attributes |
| Next hour price | The price of the next hour |
| Today average, lowest and highest price | Daily statistics |
| Cheapest and most expensive period today | The run of consecutive hours below (or above) the daily average with the lowest (or highest) average price, for example `15:00 - 19:00` |
| Cheap hour | On while the current price is at or below the daily average |
| Current gas price | EUR/m³; changes once per gas day at 06:00 |
| Current export price | What one exported kWh earns you, with today's and tomorrow's hourly values as attributes |

**Export price.** Until the end of 2026, the export price equals your contract price, because of net metering (*salderingsregeling*). From 2027 onwards it is the market price plus Budget Thuis's [ZonneBonus](https://www.budgetthuis.nl/pers/zonnebonus): by default 30% extra on a market price of up to EUR 0.20 (both adjustable, as is the period), only between sunrise and sunset, and never when the market price is zero or negative. Sunrise and sunset are approximated per month from the location of your Home Assistant. The annual cap of 5,000 kWh is not tracked.

**Timing.** Tomorrow's prices appear as soon as Budget Thuis publishes them, usually in the afternoon. Prices switch exactly on the hour, including on the days the clocks change for daylight saving time. If the tariff page is temporarily unreachable, the last known prices stay in use for as long as they cover the current hour, and the integration retries every minute.

### Using it with Omnibattery

The hourly prices use the same format as the Nord Pool integration: `raw_today` and `raw_tomorrow` with `start`, `end` and `value`, plus a `currency` attribute. In [Omnibattery](https://github.com/ffunes/Omnibattery), choose **Nordpool** as the price source and select the **Current price** sensor. For the export price, choose **Nordpool** as well and select the **Current export price** sensor.

### Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy custom_components
.venv/bin/vulture custom_components vulture_whitelist.py
.venv/bin/pytest tests --cov
```

The same checks run in CI, and test coverage must stay at 100%, branches included. The price logic (`parser.py`, `pricing.py`, `export_pricing.py`, `stats.py`) does not depend on Home Assistant. The Home Assistant glue (`coordinator.py`, `config_flow.py`, `sensor.py`, `binary_sensor.py`) is tested against a real Home Assistant test instance.

This integration is not affiliated with or endorsed by Budget Thuis.

---

## Nederlands

Een Home Assistant-integratie die de dynamische stroom- en gasprijzen van [Budget Thuis](https://www.budgetthuis.nl/) in Home Assistant zet. Zo kun je automatiseren rond goedkope en dure uren: een thuisbatterij of je auto laden, of apparaten aanzetten als stroom het goedkoopst is.

De integratie leest de openbare [tarievenpagina](https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven) van Budget Thuis. Je hebt geen account of API-sleutel nodig. De prijs voor *jouw* contract rekent de integratie zelf uit: de beursprijs en energiebelasting per uur van de pagina, plus BTW en jouw eigen inkoopvergoeding. De all-in prijs op de website wordt niet gebruikt, want daar zit jouw persoonlijke inkoopvergoeding niet in.

### Installatie

**Via HACS**

1. Open in HACS het menu (⋮) en kies **Aangepaste repositories**.
2. Voeg `https://github.com/Sarnog/ha-budgetthuis-prices` toe met als type **Integratie**.
3. Zoek **Budget Thuis Dynamic Prices**, download hem en herstart Home Assistant.

**Handmatig**

Kopieer de map `custom_components/budgetthuis` naar de map `custom_components` van je Home Assistant-configuratie en herstart Home Assistant.

**Integratie toevoegen**

Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen** en zoek op **Budget Thuis**. Je hoeft niets in te vullen; één instantie per Home Assistant is genoeg.

### Instellen

Ga naar **Instellingen → Apparaten & diensten → Budget Thuis Dynamic Prices → Configureren**.

| Instelling | Betekenis | Beginwaarde |
|---|---|---|
| Inkoopvergoeding stroom | EUR/kWh, **inclusief BTW**, precies zoals de Budget Thuis-app hem toont | 0,016822 |
| Inkoopvergoeding gas | EUR/m³, **inclusief BTW** | 0,06413 |
| BTW | Percentage | 21 |
| Extra correctie beursprijs | EUR/kWh, alleen voor bijzondere gevallen | 0 |
| ZonneBonus | Percentage bovenop de terugleverprijs vanaf 2027; 0 zet hem uit | 30 |
| ZonneBonus: maximale beursprijs | EUR/kWh | 0,20 |
| ZonneBonus vanaf / tot en met | Datums; laat de einddatum leeg voor geen einde | 1-1-2027 / leeg |

De beginwaarden zijn een startpunt en kloppen niet per se met jouw contract. Neem de bedragen over uit de tariefopbouw in de Budget Thuis-app of op mijn.budgetthuis.nl. Na het opslaan wordt alles meteen opnieuw berekend.

De prijs wordt zo berekend:

```
prijs = (beursprijs + correctie + energiebelasting) × (1 + BTW / 100) + inkoopvergoeding
```

### Entiteiten

| Entiteit | Inhoud |
|---|---|
| Huidige prijs | De prijs van dit uur in EUR/kWh, met de uurprijzen van vandaag en morgen als attributen |
| Prijs volgend uur | De prijs van het volgende uur |
| Gemiddelde, laagste en hoogste prijs vandaag | Dagstatistieken |
| Goedkoopste en duurste periode vandaag | De reeks aaneengesloten uren onder (of boven) het daggemiddelde met de laagste (of hoogste) gemiddelde prijs, bijvoorbeeld `15:00 - 19:00` |
| Goedkoop uur | Aan zolang de huidige prijs op of onder het daggemiddelde ligt |
| Huidige gasprijs | EUR/m³; verandert eens per gasdag, om 06:00 |
| Huidige terugleverprijs | Wat een teruggeleverde kWh je oplevert, met de uurwaarden van vandaag en morgen als attributen |

**Terugleverprijs.** Tot en met 2026 is de terugleverprijs gelijk aan je contractprijs, vanwege de salderingsregeling. Vanaf 2027 is het de beursprijs plus de [ZonneBonus](https://www.budgetthuis.nl/pers/zonnebonus) van Budget Thuis: standaard 30% extra over een beursprijs tot EUR 0,20 (allebei instelbaar, net als de periode), alleen tussen zonsopkomst en zonsondergang en nooit bij een beursprijs van nul of lager. Zonsopkomst en -ondergang worden per maand benaderd vanaf de locatie van je Home Assistant. De jaargrens van 5.000 kWh wordt niet bijgehouden.

**Timing.** De prijzen van morgen verschijnen zodra Budget Thuis ze publiceert, meestal in de middag. De prijzen wisselen precies op het hele uur, ook op de dagen dat de klok verzet wordt voor zomer- of wintertijd. Is de tarievenpagina even onbereikbaar, dan blijven de laatst bekende prijzen in gebruik zolang ze het huidige uur dekken, en probeert de integratie het elke minuut opnieuw.

### Gebruik met Omnibattery

De uurprijzen hebben dezelfde indeling als de Nord Pool-integratie: `raw_today` en `raw_tomorrow` met `start`, `end` en `value`, plus het attribuut `currency`. Kies in [Omnibattery](https://github.com/ffunes/Omnibattery) als prijsbron **Nordpool** en selecteer de sensor **Huidige prijs**. Kies voor de terugleverprijs ook **Nordpool** en selecteer de sensor **Huidige terugleverprijs**.

### Ontwikkelen

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy custom_components
.venv/bin/vulture custom_components vulture_whitelist.py
.venv/bin/pytest tests --cov
```

Dezelfde controles draaien in CI, en de testdekking moet 100% blijven, vertakkingen inbegrepen. De prijslogica (`parser.py`, `pricing.py`, `export_pricing.py`, `stats.py`) is los van Home Assistant. De aansluiting op Home Assistant (`coordinator.py`, `config_flow.py`, `sensor.py`, `binary_sensor.py`) wordt getest tegen een echte Home Assistant-testinstantie.

Deze integratie is niet verbonden aan of goedgekeurd door Budget Thuis.
