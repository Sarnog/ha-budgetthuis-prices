"""Inleeslogica voor de tarievenpagina van Budget Thuis.

Bewust zonder Home Assistant-imports, zodat het met gewone pytest te testen is,
los van welke HA-ontwikkelomgeving er beschikbaar is.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

from .const import NEXT_DATA_PATTERN

AMSTERDAM = ZoneInfo("Europe/Amsterdam")

# Sleutels van de tariefenlijsten per dag in de payload van de pagina. Stroom
# komt in uurblokken; gas in twee blokken per kalenderdag (00:00-06:00, nog de
# prijs van de vorige gasdag, en 06:00-24:00), omdat een gasdag om 06:00 begint.
ELECTRICITY = "ElectricityTariffs"
GAS = "GasTariffs"


class TariffParseError(Exception):
    """De tarievenpagina is niet in te lezen als uurprijzen."""


@dataclass
class HourPrice:
    """Eén tariefblok: een uur bij stroom, een deel van de dag bij gas."""

    start: datetime
    end: datetime
    price: float
    commodity_net: float | None
    energy_tax_net: float | None


# Zomertijd: de tijdstempels op de pagina zijn naïeve klokkijden in Amsterdam.
# Bij de overgang in de herfst komt 02:00-03:00 twee keer voor, bij die in het
# voorjaar helemaal niet, dus een naïeve tijdstempel zegt niet altijd welk echt
# moment bedoeld is. De hulpfuncties hieronder lossen dat op, en alle
# vergelijkingen elders gebruiken absolute tijdstippen (zie stats.hour_for).


def _localize(naive: datetime, fold: int) -> datetime:
    """Koppel Amsterdamse tijd en normaliseer via UTC.

    De omweg geeft het herhaalde uur in de herfst zijn juiste fold, en schuift
    een niet bestaande tijd bij het voorjaar (02:xx) naar het echte tijdstip.
    """
    aware = naive.replace(tzinfo=AMSTERDAM, fold=fold)
    return aware.astimezone(UTC).astimezone(AMSTERDAM)


def _parse_start(value: str, seen: set[datetime]) -> datetime:
    """Lees het begin van een blok; een eerder geziene naïeve klokkijd is de herhaling.

    De blokken staan op volgorde, dus de tweede "02:00" op de overgangsdag in de
    herfst is het uur in wintertijd (fold=1). Tijdstempels met een eigen
    UTC-verschil worden ongewijzigd overgenomen.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(AMSTERDAM)
    fold = 1 if parsed in seen else 0
    seen.add(parsed)
    return _localize(parsed, fold)


def _parse_end(value: str, start: datetime) -> datetime:
    """Lees het einde van een blok; kies zo nodig het latere herhaalde uur."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(AMSTERDAM)
    end = _localize(parsed, 0)
    if end.timestamp() <= start.timestamp():
        end = _localize(parsed, 1)
    return end


def _clip_overlaps(blocks: list[HourPrice]) -> None:
    """Laat elk blok uiterlijk eindigen waar het volgende begint.

    Een naïef einde kan de twee uren 02:00-03:00 ook niet onderscheiden, dus
    het eerste zou anders doorlopen in het tweede.
    """
    for block, following in pairwise(blocks):
        if block.end.timestamp() > following.start.timestamp():
            block.end = following.start


def parse_tariff_days(
    html: str, tariff_key: str = ELECTRICITY
) -> dict[str, list[HourPrice]]:
    """Lees de __NEXT_DATA__-payload van de tarievenpagina in als prijzen per dag.

    tariff_key kiest de commodity (ELECTRICITY of GAS). Een pagina zonder
    regels voor die commodity geeft een lege dict, geen fout.

    Volgt de uitlezing die al bewezen is in `fetchBudgetThuis` in
    node/src/providers/price-provider.js van het arandu-project.
    """
    match = re.search(NEXT_DATA_PATTERN, html, re.DOTALL)
    if not match:
        raise TariffParseError(
            "Geen __NEXT_DATA__-payload gevonden op de tarievenpagina"
        )

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as err:
        raise TariffParseError(f"Ongeldige __NEXT_DATA__-JSON: {err}") from err

    tariff_days = (payload.get("props") or {}).get("pageProps", {}).get("tariffDays")
    if not isinstance(tariff_days, list):
        raise TariffParseError("Geen tariffDays in de payload van de tarievenpagina")

    by_date: dict[str, list[HourPrice]] = {}
    for day in tariff_days:
        tariffs = day.get(tariff_key)
        if not isinstance(tariffs, list):
            continue

        hours: list[HourPrice] = []
        seen: set[datetime] = set()
        for tariff in tariffs:
            start_raw = tariff.get("Start")
            end_raw = tariff.get("End")
            if start_raw is None or end_raw is None:
                continue
            # Vóór de prijscontrole, zodat een overgeslagen eerste 02:00-blok de
            # volgende 02:00 toch als herhaald uur markeert.
            start = _parse_start(start_raw, seen)
            total = tariff.get("TotalTariff") or {}
            price = total.get("AmountGross")
            if price is None:
                continue

            hours.append(
                HourPrice(
                    start=start,
                    end=_parse_end(end_raw, start),
                    price=float(price),
                    commodity_net=(tariff.get("Commodity") or {}).get("AmountNet"),
                    energy_tax_net=(tariff.get("EnergyTax") or {}).get("AmountNet"),
                )
            )

        if hours:
            hours.sort(key=lambda h: h.start.timestamp())
            _clip_overlaps(hours)
            by_date[hours[0].start.date().isoformat()] = hours

    return by_date
