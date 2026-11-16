# Wijzigingen

## 0.4.0

### Toegevoegd
- Diagnostiek: via *Diagnostiek downloaden* krijg je de instellingen en een overzicht van de ingelezen dagen, handig bij een probleemmelding.

### Gewijzigd
- De uurlijsten `raw_today` en `raw_tomorrow` worden niet meer in de recorder opgeslagen. Ze staan nog steeds op de sensor; alleen de geschiedenis van die attributen verdwijnt, wat de database klein houdt. De sensorwaarden zelf worden gewoon bewaard.
- Iconen komen uit `icons.json` in plaats van uit de code. Ze zien er hetzelfde uit.

### Intern
- Opgedeeld per taak: `api.py` (ophalen), `models.py` (datamodellen), `entity.py` (gedeelde basisklasse en apparaat, vervangt `helpers.py`). `binary_sensor.py` gebruikt nu dezelfde basisklasse als de sensors in plaats van een kopie.
- `NEXT_DATA_PATTERN` staat in `parser.py`, de enige plek die het gebruikt.
- Entity-ID's en unieke ID's zijn ongewijzigd.

## 0.3.3

### Gewijzigd
- README herschreven, volledig in het Engels en het Nederlands.
- `hacs.json` vermeldt nu het land (`NL`), zodat HACS de integratie bij Nederlandse gebruikers toont.

### Intern
- De coordinator staat in `entry.runtime_data` in plaats van in `hass.data`, met een getypeerde config entry. Dat is het huidige patroon van Home Assistant; Home Assistant ruimt de coordinator nu zelf op bij het ontladen.
- Platforms als `Platform`-enum in plaats van losse tekst.
- Bij het ophalen worden alleen netwerkfouten en time-outs afgevangen (`aiohttp.ClientError`, `TimeoutError`) in plaats van elke uitzondering, zodat echte programmeerfouten zichtbaar blijven in het log.

## 0.3.2

### Opgelost
- Eén mislukte ophaalronde (bijvoorbeeld een 502 van de Budget Thuis-site) maakte alle sensors een uur lang onbeschikbaar, terwijl de prijzen van vandaag al binnen waren. Prijsgestuurde integraties zoals Omnibattery stopten daardoor met ontladen. Nu blijven de laatst bekende prijzen in gebruik zolang ze het huidige uur dekken, en wordt het elke minuut opnieuw geprobeerd tot het ophalen weer lukt. Pas als er geen prijs meer is voor het huidige uur, worden de sensors onbeschikbaar.

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
