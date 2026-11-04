# Wijzigingen

## 0.3.1

### Toegevoegd
- Opties *ZonneBonus vanaf* (standaard 1-1-2027) en *ZonneBonus tot en met* (standaard leeg, geen einde), zodat de bonus op een eigen datum aan en uit gaat als Budget Thuis de actie verschuift of stopt. Het einde van de saldering blijft 1-1-2027.

## 0.3.0

### Toegevoegd
- Sensor *Huidige terugleverprijs* (`current_export_price`) met `raw_today`, `raw_tomorrow` en `currency` in de indeling van Nord Pool, zodat Omnibattery hem als terugleverprijs kan lezen. Tot en met 2026 is de waarde de contractprijs (saldering), vanaf 2027 de beursprijs plus de ZonneBonus van Budget Thuis.
- Opties voor de ZonneBonus: het percentage (standaard 30, 0 = uit) en de maximale beursprijs waarover de bonus telt (standaard EUR 0,20).

## 0.2.0

### Toegevoegd
- Elk uur in `raw_today` en `raw_tomorrow` heeft nu ook `value` (gelijk aan `price`) en de sensor `current_price` het attribuut `currency`. Dat is de indeling van Nord Pool (HACS), waarmee prijsgestuurde integraties zoals Omnibattery de sensor direct kunnen lezen.
- Nederlandse vertaling (`nl.json`): de namen van de entiteiten en de teksten van de instellingen.

### Gewijzigd
- Prijzen worden op 5 decimalen bewaard in plaats van op 3, zoals mijn.budgetthuis.nl ze toont. Het gemiddelde van vandaag komt zo overeen met de contractpagina, en de twee gasblokken van een dag houden hun eigen prijs. De weergave in Home Assistant blijft op 3 decimalen.
- Commentaar, documentatie en foutmeldingen zijn Nederlands.
- Entiteitsnamen komen uit de vertalingen. Bestaande entiteiten houden hun entity-ID; alleen de weergavenaam volgt de taal van Home Assistant.

### Intern
- Tests voor de config flow, de opties, foutsituaties en de sensors; 100% branch-coverage.
- CI draait ruff, mypy (strict), vulture en pytest met Home Assistant.
