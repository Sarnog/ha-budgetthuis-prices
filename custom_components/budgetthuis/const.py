"""Constanten voor de integratie Budget Thuis Dynamic Prices."""

from datetime import timedelta

DOMAIN = "budgetthuis"

TARIFF_URL = (
    "https://www.budgetthuis.nl/energie/klantenservice/actuele-dynamische-tarieven"
)

NEXT_DATA_PATTERN = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'

# Budget Thuis publiceert de tarieven van morgen in de middag, net als de
# day-ahead-veiling waar ze van zijn afgeleid. Elk uur ophalen is genoeg om dat
# snel op te pikken zonder de site te belasten.
UPDATE_INTERVAL = timedelta(hours=1)

# Mislukt het ophalen (bijvoorbeeld een 502 van de site), dan blijven de bekende
# prijzen staan zolang ze het huidige uur dekken, en wordt het elke minuut
# opnieuw geprobeerd tot het weer lukt. Daarna geldt weer UPDATE_INTERVAL.
RETRY_INTERVAL = timedelta(minutes=1)

# De entiteitstoestanden worden op dit klokraster opnieuw bepaald, los van het
# ophalen hierboven: het moment van ophalen hangt af van wanneer Home Assistant
# startte (bijvoorbeeld 14:23, 15:23, ...), en daarop vertrouwen liet de prijs
# van het vorige uur te lang staan. De pagina heeft nu uurprijzen voor stroom en
# grenzen om 00:00/06:00 voor gas; elk kwartier controleren dekt ook een latere
# overstap naar kwartierprijzen. Er wordt alleen in de opgeslagen gegevens
# gelezen, er komt geen extra verzoek bij.
PRICE_TICK_MINUTES = (0, 15, 30, 45)

# Prijzen worden op 5 decimalen bewaard, de precisie waarmee mijn.budgetthuis.nl
# ze toont. Per uur afronden op 3 decimalen liet het daggemiddelde tot
# EUR 0,001 afwijken van wat Budget Thuis zelf meldt (0,433 tegenover 0,43353)
# en maakte van de twee gasblokken (2,02694 en 2,02712) allebei 2,027. De
# weergave in Home Assistant blijft op 3 decimalen (suggested_display_precision).
PRICE_DECIMALS = 5

CURRENCY = "EUR"
CURRENCY_EUR_PER_KWH = "EUR/kWh"
CURRENCY_EUR_PER_M3 = "EUR/m³"

# Opties voor de contractprijs (opties-flow van Home Assistant), naar het
# voorbeeld van het tarievenscherm in de Budget Thuis-app: beursprijs (live per
# uur, al ingelezen) + energiebelasting met 21% BTW, plus de inkoopvergoeding,
# die de app al inclusief BTW toont. De energiebelasting is een overheidstarief
# en het netto bedrag staat per uur op de tarievenpagina, dus dat wordt live
# gelezen (zie pricing.py) in plaats van ingesteld. "Stroom gemiddeld" in de app
# is alleen de uitkomst, geen aparte invoer.
CONF_INKOOPVERGOEDING = "inkoopvergoeding"
CONF_VAT_PERCENT = "vat_percent"
CONF_BEURSPRIJS_MARKUP = "beursprijs_markup"
# Gas heeft een eigen inkoopvergoeding (EUR/m³, incl. BTW); de BTW is gelijk aan
# die van stroom.
CONF_GAS_INKOOPVERGOEDING = "gas_inkoopvergoeding"

# Alleen beginwaarden: stem ze af op de tariefopbouw van het eigen contract in de
# Budget Thuis-app. Beide inkoopvergoedingen zijn inclusief BTW, zoals de app ze
# toont.
DEFAULT_INKOOPVERGOEDING = 0.016822
DEFAULT_VAT_PERCENT = 21.0
DEFAULT_BEURSPRIJS_MARKUP = 0.0
DEFAULT_GAS_INKOOPVERGOEDING = 0.06413

# Terugleverprijs. Tot en met 2026 geldt de salderingsregeling: teruggeleverde
# stroom wordt verrekend met afgenomen stroom, dus een teruggeleverde kWh is dan
# evenveel waard als de contractprijs van dat uur. Vanaf 1 januari 2027 vervalt
# saldering en betaalt Budget Thuis bij een dynamisch contract de beursprijs
# (zonder BTW en zonder terugleverkosten), plus de ZonneBonus: 30% extra over een
# beursprijs tot EUR 0,20, alleen tussen zonsopkomst en zonsondergang en niet bij
# een beursprijs van nul of lager. Zie https://www.budgetthuis.nl/pers/zonnebonus.
# De ZonneBonus is een actie die Budget Thuis kan aanpassen of stoppen, dus het
# percentage, de maximale beursprijs en de periode zijn opties (0% zet de bonus
# uit, een lege einddatum betekent geen einde). Het einde van de saldering is
# wettelijk en dus geen optie. De grens van de eerste 5.000 kWh per
# leveringsjaar wordt niet bijgehouden.
SALDERING_END_YEAR = 2027
CONF_ZONNEBONUS_PERCENT = "zonnebonus_percent"
CONF_ZONNEBONUS_MAX_BEURSPRIJS = "zonnebonus_max_beursprijs"
CONF_ZONNEBONUS_FROM = "zonnebonus_from"
CONF_ZONNEBONUS_UNTIL = "zonnebonus_until"
DEFAULT_ZONNEBONUS_PERCENT = 30.0
DEFAULT_ZONNEBONUS_MAX_BEURSPRIJS = 0.20
DEFAULT_ZONNEBONUS_FROM = "2027-01-01"
