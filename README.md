# Budget Thuis Dynamic Prices

Home Assistant-integratie met de dynamische stroom- en gasprijzen van [Budget Thuis](https://www.budgetthuis.nl/), voor automatiseringen rond goedkope en dure uren (batterij, auto laden, apparaten plannen).

De integratie leest de openbare [tarievenpagina](https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven). Je hebt geen account of API-sleutel nodig. De prijs rekent ze zelf uit voor jouw contract: de actuele beursprijs en energiebelasting van de pagina, plus BTW en jouw eigen inkoopvergoeding. De prijs die de site zelf toont is niet bruikbaar, want daar zit jouw inkoopvergoeding niet in.

## Installatie

1. HACS → Integraties → ⋮ → Aangepaste repositories → voeg deze repository toe als categorie *Integratie*.
2. Installeer *Budget Thuis Dynamic Prices* en herstart Home Assistant.
3. Instellingen → Apparaten & diensten → Integratie toevoegen → *Budget Thuis*.

## Instellen

Instellingen → Apparaten & diensten → Budget Thuis Dynamic Prices → Configureren.

| Instelling | Betekenis | Beginwaarde |
|---|---|---|
| Inkoopvergoeding stroom | EUR/kWh, **incl. BTW**, zoals de Budget Thuis-app hem toont | 0,016822 |
| Inkoopvergoeding gas | EUR/m³, **incl. BTW** | 0,06413 |
| BTW | percentage | 21 |
| Extra correctie beursprijs | EUR/kWh, voor bijzondere gevallen | 0 |
| ZonneBonus | %, vanaf 2027 op de terugleverprijs; 0 = uit | 30 |
| ZonneBonus: maximale beursprijs | EUR/kWh | 0,20 |
| ZonneBonus vanaf / tot en met | datums; leeg einde = geen einde | 1-1-2027 / leeg |

De beginwaarden kloppen niet per se met jouw contract. Neem de bedragen over uit de tariefopbouw in de Budget Thuis-app of op mijn.budgetthuis.nl. Na het opslaan wordt alles direct opnieuw berekend.

Prijs = (beursprijs + correctie + energiebelasting) × (1 + BTW) + inkoopvergoeding.

## Entiteiten

| Entiteit | Inhoud |
|---|---|
| Huidige prijs | Prijs van dit uur in EUR/kWh, met de uurprijzen van vandaag en morgen als attributen |
| Prijs volgend uur | Prijs van het volgende uur |
| Gemiddelde, laagste en hoogste prijs vandaag | Dagstatistieken |
| Goedkoopste en duurste periode vandaag | Aaneengesloten reeks uren onder of boven het gemiddelde, bijvoorbeeld `15:00 - 19:00` |
| Goedkoop uur | Aan zolang de prijs op of onder het daggemiddelde ligt |
| Huidige gasprijs | EUR/m³, verandert eens per gasdag om 06:00 |
| Huidige terugleverprijs | Opbrengst van een teruggeleverde kWh, met de uurwaarden van vandaag en morgen als attributen |

De terugleverprijs is tot en met 2026 gelijk aan de contractprijs (saldering). Vanaf 2027 is het de beursprijs plus de [ZonneBonus](https://www.budgetthuis.nl/pers/zonnebonus): standaard 30% extra over een beursprijs tot EUR 0,20 (instelbaar, net als de periode), tussen zonsopkomst en zonsondergang, niet bij een beursprijs van nul of lager. Het tijdvak wordt per maand benaderd uit de zonsopkomst en -ondergang op de locatie van Home Assistant. De grens van 5.000 kWh per jaar wordt niet bijgehouden.

De prijzen van morgen verschijnen zodra Budget Thuis ze publiceert, meestal in de middag. De prijzen schuiven op het hele uur door, ook rond de zomer- en wintertijd.

## Gebruik met Omnibattery

De uurprijzen staan in de indeling van Nord Pool: `raw_today` en `raw_tomorrow` met `start`, `end` en `value`, plus `currency`. Kies in [Omnibattery](https://github.com/ffunes/Omnibattery) als prijsbron *Nordpool* en selecteer de sensor *Huidige prijs*. Kies als terugleverprijs ook *Nordpool* met de sensor *Huidige terugleverprijs*.

## Ontwikkelen

```
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy custom_components
.venv/bin/vulture custom_components vulture_whitelist.py
.venv/bin/pytest tests --cov
```

Dezelfde controles draaien in CI. De dekking moet 100% zijn, inclusief vertakkingen. De berekening (`parser.py`, `pricing.py`, `stats.py`) heeft geen Home Assistant nodig; `coordinator.py`, `config_flow.py`, `sensor.py` en `binary_sensor.py` zijn de aansluiting op Home Assistant en worden met een echte testinstantie getest.
